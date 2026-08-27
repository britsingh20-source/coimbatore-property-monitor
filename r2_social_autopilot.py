from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

import boto3
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from meta_publisher import (
    GRAPH,
    POLL_ATTEMPTS,
    POLL_SECONDS,
    _required,
    _response_json,
    publish_facebook_reel,
    publish_instagram_reel,
    validate_page_token,
)
from social_content import build_social_content
from video_property_matcher import match_uploaded_video


PREFIX = os.environ.get("R2_SOCIAL_PREFIX", "social-ready/").strip().lstrip("/")
STATE_PATH = Path(os.environ.get("SOCIAL_STATE_PATH", "data/social_publish_state.json"))
QUEUE_PATH = Path(os.environ.get("TELEGRAM_PROMPT_QUEUE", "data/telegram_prompt_queue.json"))
MAX_PER_RUN = max(1, int(os.environ.get("SOCIAL_MAX_PER_RUN", "1")))
DRY_RUN = os.environ.get("SOCIAL_DRY_RUN", "false").lower() == "true"
PUBLIC_PLATFORMS = ("instagram_reel", "instagram_story", "youtube_short")
YOUTUBE_SHORT_MAX_SECONDS = 180.0
YOUTUBE_SHORT_WIDTH = 1080
YOUTUBE_SHORT_HEIGHT = 1920


def _r2():
    account_id = _required("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=_required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


def _load_state() -> dict:
    if not STATE_PATH.exists():
        return {"objects": {}}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_queue() -> dict:
    if not QUEUE_PATH.exists():
        return {"prompts": []}
    return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))


def _save_queue(queue: dict) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _resolve_video_id(key: str, etag: str, video_url: str, state: dict, queue: dict) -> str:
    record = state["objects"].get(key)
    if record and record.get("video_id"):
        return str(record["video_id"])

    assigned_prompt = next(
        (
            item for item in queue.get("prompts", [])
            if item.get("r2_key") == key and item.get("video_id")
        ),
        None,
    )
    filename_id = Path(key).stem
    filename_job = Path("data/video_jobs") / f"{filename_id}.json"
    match_result = None
    if assigned_prompt is not None:
        video_id = str(assigned_prompt["video_id"]).strip()
        assigned_job = Path("data/video_jobs") / f"{video_id}.json"
        if not assigned_job.exists():
            raise RuntimeError(f"Assigned VIDEO_ID has no property job: {video_id}")
        match_result = {
            "method": "telegram_exact_video_id",
            "confidence": 1.0,
        }
    elif filename_job.exists():
        video_id = filename_id
    else:
        ingest_path = Path(os.environ.get("TELEGRAM_INGEST_STATE", "data/telegram_ingest_state.json"))
        ingest_state = (
            json.loads(ingest_path.read_text(encoding="utf-8"))
            if ingest_path.exists()
            else {"files": {}}
        )
        upload_record = next(
            (
                item for item in ingest_state.get("files", {}).values()
                if item.get("r2_key") == key
            ),
            None,
        )
        if upload_record and upload_record.get("status") == "uploaded_awaiting_video_id":
            state["objects"][key] = {
                "etag": etag,
                "status": "waiting_for_video_id",
                "platforms": {},
            }
            _save_state(state)
            print(f"WAITING {key}: exact Telegram VIDEO_ID has not been supplied")
            return ""
        pending_ids = [
            str(item.get("video_id") or "").strip()
            for item in queue.get("prompts", [])
            if item.get("status") == "pending_mobile_upload"
        ]
        if upload_record and upload_record.get("candidate_video_ids"):
            allowed_at_upload = set(upload_record.get("candidate_video_ids") or [])
            pending_ids = [video_id for video_id in pending_ids if video_id in allowed_at_upload]
        pending_ids = [
            video_id for video_id in pending_ids
            if video_id and (Path("data/video_jobs") / f"{video_id}.json").exists()
        ]
        try:
            match_result = None
            for attempt in range(3):
                try:
                    match_result = match_uploaded_video(video_url, pending_ids)
                    break
                except Exception as retry_error:
                    if "429" not in str(retry_error) or attempt == 2:
                        raise
                    wait_seconds = 15 * (attempt + 1)
                    print(f"Gemini matcher rate-limited; retrying in {wait_seconds}s")
                    time.sleep(wait_seconds)
            if match_result is None:
                raise RuntimeError("Gemini matcher returned no result")
        except Exception as error:
            state["objects"][key] = {
                "etag": etag,
                "status": "match_error",
                "match_error": str(error)[:3000],
                "candidate_video_ids": pending_ids,
                "platforms": {},
            }
            _save_state(state)
            print(f"MATCH ERROR {key}: {error}")
            return ""
        video_id = str(match_result.get("video_id") or "").strip()
        if not video_id:
            state["objects"][key] = {
                "etag": etag,
                "status": "unmatched",
                "match_analysis": match_result,
                "platforms": {},
            }
            _save_state(state)
            print(
                f"UNMATCHED {key}: confidence={match_result.get('confidence', 0)}; "
                f"no publishing attempted"
            )
            return ""

    prompt = next(
        (item for item in queue.get("prompts", []) if item.get("video_id") == video_id),
        None,
    )
    state["objects"][key] = {
        "etag": etag,
        "video_id": video_id,
        "status": "matched",
        "match_analysis": match_result or {
            "method": "exact_filename",
            "confidence": 1.0,
        },
        "platforms": {},
    }
    if prompt is not None:
        prompt["status"] = "assigned_to_r2_upload"
        prompt["r2_key"] = key
    _save_state(state)
    _save_queue(queue)
    print(f"CONTENT-MATCHED mobile upload {key} -> property {video_id}")
    return video_id


def _wait_instagram(creation_id: str, token: str) -> dict:
    last = {}
    for _ in range(POLL_ATTEMPTS):
        response = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        last = _response_json(response)
        status = str(last.get("status_code", "")).upper()
        if status == "FINISHED":
            return last
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {json.dumps(last, ensure_ascii=False)}")
        time.sleep(POLL_SECONDS)
    raise RuntimeError(f"Instagram container timed out: {json.dumps(last, ensure_ascii=False)}")


def publish_instagram_story(video_url: str) -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    ig_user_id = _required("META_IG_USER_ID")
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": token,
        },
        timeout=60,
    )
    creation_id = str(_response_json(response).get("id", ""))
    if not creation_id:
        raise RuntimeError("Instagram Story container did not return an id")
    processing = _wait_instagram(creation_id, token)
    response = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    result = _response_json(response)
    return {"creation_id": creation_id, "media_id": result.get("id"), "processing": processing}


def delete_instagram_media(media_id: str) -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    response = requests.delete(
        f"{GRAPH}/{media_id}",
        params={"access_token": token},
        timeout=60,
    )
    return _response_json(response)


def delete_youtube_video(video_id: str) -> dict:
    credentials = Credentials(
        token=None,
        refresh_token=_required("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_required("YOUTUBE_CLIENT_ID"),
        client_secret=_required("YOUTUBE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    youtube.videos().delete(id=video_id).execute()
    return {"video_id": video_id, "deleted": True}


def _probe_video(video_path: Path) -> dict:
    """Return video and audio details used by the Shorts eligibility gate."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,sample_rate,channels,channel_layout,bit_rate:format=duration",
            "-of", "json", str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if video_stream is None:
        raise RuntimeError("Uploaded MP4 has no video stream")
    return {
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "duration": float((payload.get("format") or {}).get("duration") or 0),
        "audio_codec": str((audio_stream or {}).get("codec_name") or ""),
        "audio_sample_rate": int((audio_stream or {}).get("sample_rate") or 0),
        "audio_channels": int((audio_stream or {}).get("channels") or 0),
        "audio_channel_layout": str((audio_stream or {}).get("channel_layout") or ""),
        "audio_bit_rate": int((audio_stream or {}).get("bit_rate") or 0),
    }


def prepare_youtube_short(source_path: Path, output_path: Path) -> dict:
    """Create a guaranteed 9:16 MP4 before calling YouTube's normal upload API.

    YouTube has no API flag that turns a landscape upload into a Short. It
    classifies an eligible upload from its aspect ratio and duration, so every
    mobile upload is normalized even when Gemini ignored the portrait prompt.
    Landscape footage is fitted over a blurred full-frame background to avoid
    cropping the property's elevation or embedded information footer.
    """
    source = _probe_video(source_path)
    if source["duration"] <= 0:
        raise RuntimeError("Could not determine uploaded MP4 duration")
    if source["duration"] > YOUTUBE_SHORT_MAX_SECONDS:
        raise RuntimeError(
            f"Video is {source['duration']:.1f}s; YouTube Shorts must be no longer "
            f"than {YOUTUBE_SHORT_MAX_SECONDS:.0f}s"
        )

    portrait_ratio = YOUTUBE_SHORT_HEIGHT / YOUTUBE_SHORT_WIDTH
    source_ratio = source["height"] / max(1, source["width"])
    if source_ratio >= portrait_ratio * 0.90:
        video_filter = (
            f"[0:v]scale={YOUTUBE_SHORT_WIDTH}:{YOUTUBE_SHORT_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={YOUTUBE_SHORT_WIDTH}:{YOUTUBE_SHORT_HEIGHT},"
            "setsar=1,fps=30,format=yuv420p[outv]"
        )
        layout = "portrait_crop"
    else:
        video_filter = (
            "[0:v]split=2[background][foreground];"
            f"[background]scale={YOUTUBE_SHORT_WIDTH}:{YOUTUBE_SHORT_HEIGHT}:"
            "force_original_aspect_ratio=increase,"
            f"crop={YOUTUBE_SHORT_WIDTH}:{YOUTUBE_SHORT_HEIGHT},"
            "boxblur=24:2[blurred];"
            f"[foreground]scale={YOUTUBE_SHORT_WIDTH}:{YOUTUBE_SHORT_HEIGHT}:"
            "force_original_aspect_ratio=decrease[main];"
            "[blurred][main]overlay=(W-w)/2:(H-h)/2,"
            "setsar=1,fps=30,format=yuv420p[outv]"
        )
        layout = "landscape_blurred_fill"

    if source["audio_codec"] == "aac":
        # The Telegram/Gemini MP4 already contains YouTube-compatible AAC.
        # Copy it bit-for-bit: encoding it here and again at YouTube caused
        # audible metallic/strained voice artifacts on the first converted Short.
        audio_args = ["-c:a", "copy"]
        audio_handling = "copied_original_aac"
    else:
        audio_args = ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
        audio_handling = "aac_fallback_encode" if source["audio_codec"] else "no_audio"

    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source_path),
            "-filter_complex", video_filter,
            "-map", "[outv]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            *audio_args,
            "-movflags", "+faststart", "-shortest", str(output_path),
        ],
        check=True,
    )
    normalized = _probe_video(output_path)
    if normalized["width"] != YOUTUBE_SHORT_WIDTH or normalized["height"] != YOUTUBE_SHORT_HEIGHT:
        raise RuntimeError(
            "YouTube Short normalization failed: expected 1080x1920, got "
            f"{normalized['width']}x{normalized['height']}"
        )
    return {
        "source": source,
        "output": normalized,
        "layout": layout,
        "audio_handling": audio_handling,
    }


def publish_facebook_story(video_path: Path) -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    page = validate_page_token()
    response = requests.post(
        f"{GRAPH}/me/video_stories",
        data={"upload_phase": "start", "access_token": token},
        timeout=60,
    )
    started = _response_json(response)
    video_id = str(started.get("video_id", ""))
    upload_url = str(started.get("upload_url", ""))
    if not video_id or not upload_url:
        raise RuntimeError(f"Facebook Story start response incomplete: {json.dumps(started, ensure_ascii=False)}")

    size = video_path.stat().st_size
    with video_path.open("rb") as handle:
        uploaded = _response_json(requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(size),
                "Content-Type": "application/octet-stream",
            },
            data=handle,
            timeout=600,
        ))
    finished = _response_json(requests.post(
        f"{GRAPH}/me/video_stories",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "access_token": token,
        },
        timeout=60,
    ))
    return {"page": page, "video_id": video_id, "upload": uploaded, "finish": finished}


def publish_youtube_short(video_path: Path, title: str, description: str) -> dict:
    credentials = Credentials(
        token=None,
        refresh_token=_required("YOUTUBE_REFRESH_TOKEN"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=_required("YOUTUBE_CLIENT_ID"),
        client_secret=_required("YOUTUBE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": ["Shorts", "Coimbatore Property", "Coimbatore Real Estate", "Property For Sale"],
                "categoryId": "22",
            },
            "status": {
                "privacyStatus": os.environ.get("YOUTUBE_PRIVACY_STATUS", "public"),
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return {"video_id": response.get("id"), "status": response.get("status"), "snippet": response.get("snippet")}


def _available(platform: str) -> bool:
    required = {
        "instagram_reel": ("META_PAGE_ACCESS_TOKEN", "META_IG_USER_ID"),
        "facebook_reel": ("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID"),
        "instagram_story": ("META_PAGE_ACCESS_TOKEN", "META_IG_USER_ID"),
        "facebook_story": ("META_PAGE_ACCESS_TOKEN", "META_PAGE_ID"),
        "youtube_short": ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"),
    }[platform]
    return all(os.environ.get(name, "").strip() for name in required)


def _publish_one(key: str, etag: str, client, bucket: str, state: dict, queue: dict) -> bool:
    video_url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=21600,
    )
    video_id = _resolve_video_id(key, etag, video_url, state, queue)
    if not video_id:
        return False
    job_path = Path("data/video_jobs") / f"{video_id}.json"
    record = state["objects"][key]
    if record.get("etag") != etag:
        record.update({"etag": etag, "platforms": {}})
    content = build_social_content(json.loads(job_path.read_text(encoding="utf-8")))
    record["content"] = content

    if record.get("correction_pending"):
        deletion_results: dict[str, dict] = {}
        deletion_failures: list[str] = []
        for platform in ("instagram_reel", "instagram_story"):
            media_id = str(record.get("platforms", {}).get(platform, {}).get("result", {}).get("media_id") or "")
            if not media_id:
                continue
            try:
                deletion_results[platform] = delete_instagram_media(media_id)
                print(f"DELETED incorrect {platform}: {media_id}")
            except Exception as error:
                deletion_failures.append(f"{platform}: {error}")
        youtube_id = str(record.get("platforms", {}).get("youtube_short", {}).get("result", {}).get("video_id") or "")
        if youtube_id:
            try:
                deletion_results["youtube_short"] = delete_youtube_video(youtube_id)
                print(f"DELETED incorrect youtube_short: {youtube_id}")
            except Exception as error:
                deletion_failures.append(f"youtube_short: {error}")
        record["correction_deletions"] = deletion_results
        if deletion_failures:
            record["correction_status"] = "deletion_failed"
            record["correction_errors"] = deletion_failures
            _save_state(state)
            raise RuntimeError("Correction deletion failed; republish blocked: " + " | ".join(deletion_failures))
        record["platforms"] = {}
        record["correction_pending"] = False
        record["correction_status"] = "deleted_awaiting_republish"
        _save_state(state)

    with tempfile.TemporaryDirectory(prefix="property-social-") as temp_dir:
        video_path = Path(temp_dir) / f"{video_id}.mp4"
        youtube_path = Path(temp_dir) / f"{video_id}-youtube-short.mp4"
        client.download_file(bucket, key, str(video_path))
        if video_path.stat().st_size < 100_000:
            raise RuntimeError(f"R2 video is too small: {key}")
        youtube_media = prepare_youtube_short(video_path, youtube_path)
        record["youtube_media"] = youtube_media
        _save_state(state)
        print(
            "YOUTUBE SHORT READY "
            f"{video_id}: {youtube_media['source']['width']}x{youtube_media['source']['height']} -> "
            f"{youtube_media['output']['width']}x{youtube_media['output']['height']} "
            f"({youtube_media['layout']})"
        )
        if record.get("youtube_republish_pending"):
            old_youtube_id = str(
                record.get("platforms", {})
                .get("youtube_short", {})
                .get("result", {})
                .get("video_id")
                or ""
            )
            if old_youtube_id:
                try:
                    deletion = delete_youtube_video(old_youtube_id)
                    record["youtube_republish_deletion"] = deletion
                    print(f"DELETED disturbed youtube_short before audio-safe replacement: {old_youtube_id}")
                except Exception as error:
                    # Existing OAuth credentials may have youtube.upload scope
                    # without delete permission. Do not block the corrected
                    # upload; retain the old ID for manual Studio cleanup.
                    record["youtube_republish_deletion"] = {
                        "video_id": old_youtube_id,
                        "deleted": False,
                        "error": str(error)[:1500],
                        "manual_cleanup_required": True,
                    }
                    print(
                        "OLD youtube_short could not be deleted; publishing "
                        f"audio-safe replacement and retaining {old_youtube_id} "
                        "for manual cleanup"
                    )
            record.setdefault("platforms", {}).pop("youtube_short", None)
            record["youtube_republish_pending"] = False
            _save_state(state)
        publishers: dict[str, Callable[[], dict]] = {
            "instagram_reel": lambda: publish_instagram_reel(video_url, str(content["caption"])),
            "facebook_reel": lambda: publish_facebook_reel(video_path, str(content["caption"])),
            "instagram_story": lambda: publish_instagram_story(video_url),
            "facebook_story": lambda: publish_facebook_story(video_path),
            "youtube_short": lambda: publish_youtube_short(
                youtube_path, str(content["title"]), str(content["youtube_description"])
            ),
        }
        for platform in PUBLIC_PLATFORMS:
            if record["platforms"].get(platform, {}).get("status") == "published":
                continue
            if not _available(platform):
                record["platforms"][platform] = {"status": "waiting_for_secrets"}
                print(f"WAITING {platform}: required secrets are not configured")
                continue
            if DRY_RUN:
                record["platforms"][platform] = {"status": "dry_run"}
                continue
            try:
                result = publishers[platform]()
                record["platforms"][platform] = {"status": "published", "result": result}
                print(f"PUBLISHED {video_id} -> {platform}")
            except Exception as error:
                record["platforms"][platform] = {"status": "failed", "error": str(error)[:1500]}
                print(f"FAILED {video_id} -> {platform}: {error}")
            finally:
                _save_state(state)

    if all(record["platforms"].get(p, {}).get("status") == "published" for p in PUBLIC_PLATFORMS):
        prompt = next((item for item in queue.get("prompts", []) if item.get("video_id") == video_id), None)
        if prompt is not None:
            prompt["status"] = "published"
            prompt["r2_key"] = key
            _save_queue(queue)
    return True


def main() -> None:
    bucket = _required("R2_BUCKET_NAME")
    client = _r2()
    state = _load_state()
    queue = _load_queue()
    response = client.list_objects_v2(Bucket=bucket, Prefix=PREFIX)
    objects = [
        item for item in response.get("Contents", [])
        if str(item.get("Key", "")).lower().endswith(".mp4")
    ]
    assigned_keys = {
        str(item.get("r2_key") or "")
        for item in queue.get("prompts", [])
        if item.get("status") == "assigned_to_r2_upload" and item.get("r2_key")
    }
    objects.sort(
        key=lambda item: (
            0 if str(item.get("Key") or "") in assigned_keys else 1,
            item.get("LastModified"),
        )
    )
    processed = 0
    processed_keys: list[str] = []
    for item in objects:
        key = str(item["Key"])
        etag = str(item.get("ETag", "")).strip('"')
        platforms = state.get("objects", {}).get(key, {}).get("platforms", {})
        correction_pending = bool(state.get("objects", {}).get(key, {}).get("correction_pending"))
        youtube_republish_pending = bool(
            state.get("objects", {}).get(key, {}).get("youtube_republish_pending")
        )
        if not correction_pending and not youtube_republish_pending and all(
            platforms.get(p, {}).get("status") == "published" for p in PUBLIC_PLATFORMS
        ):
            continue
        if _publish_one(key, etag, client, bucket, state, queue):
            processed += 1
            processed_keys.append(key)
        if processed >= MAX_PER_RUN:
            break
    _save_state(state)
    _save_queue(queue)
    print(f"R2 social scan complete: {len(objects)} video(s), processed {processed}")
    failures = [
        f"{key}: {platform}: {details.get('error', 'unknown error')}"
        for key in processed_keys
        for platform, details in state["objects"][key]["platforms"].items()
        if details.get("status") == "failed"
    ]
    if failures:
        raise RuntimeError("Social publishing failures:\\n" + "\\n".join(failures))


if __name__ == "__main__":
    main()
