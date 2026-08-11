import argparse
import json
import os
import time
from pathlib import Path

import boto3
import requests


GRAPH_VERSION = os.environ.get("META_GRAPH_VERSION", "v26.0").strip()
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
POLL_SECONDS = int(os.environ.get("META_POLL_SECONDS", "8"))
POLL_ATTEMPTS = int(os.environ.get("META_POLL_ATTEMPTS", "30"))
PRESIGNED_SECONDS = int(os.environ.get("META_MEDIA_URL_TTL", "21600"))
IG_THUMB_OFFSET_MS = int(os.environ.get("META_IG_THUMB_OFFSET_MS", "2000"))


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _response_json(response: requests.Response) -> dict:
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text[:1000]}
    if not response.ok:
        raise RuntimeError(f"Meta API HTTP {response.status_code}: {json.dumps(data, ensure_ascii=False)[:1500]}")
    return data


def validate_page_token() -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    configured_page_id = _required("META_PAGE_ID")
    response = requests.get(
        f"{GRAPH}/me",
        params={"fields": "id,name", "access_token": token},
        timeout=30,
    )
    identity = _response_json(response)
    resolved_page_id = str(identity.get("id", "")).strip()
    if not resolved_page_id:
        raise RuntimeError("Meta Page token identity did not return an id")
    if resolved_page_id != configured_page_id:
        raise RuntimeError(
            "META_PAGE_ACCESS_TOKEN is not acting as the configured Facebook Page: "
            f"token resolves to id={resolved_page_id}, configured META_PAGE_ID={configured_page_id}. "
            "Use the Page access token returned for this Page by /me/accounts, not the User access token."
        )
    return {"id": resolved_page_id, "name": identity.get("name")}


def upload_to_r2(video_path: Path, video_id: str) -> tuple[str, str]:
    account_id = _required("R2_ACCOUNT_ID")
    bucket = _required("R2_BUCKET_NAME")
    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=_required("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_required("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )
    key = f"social-publish/{video_id}/{video_path.name}"
    client.upload_file(
        str(video_path),
        bucket,
        key,
        ExtraArgs={"ContentType": "video/mp4"},
    )
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=PRESIGNED_SECONDS,
    )
    return key, url


def publish_instagram_reel(video_url: str, caption: str) -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    ig_user_id = _required("META_IG_USER_ID")

    create = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "thumb_offset": str(max(0, IG_THUMB_OFFSET_MS)),
            "access_token": token,
        },
        timeout=60,
    )
    container = _response_json(create)
    creation_id = str(container.get("id", ""))
    if not creation_id:
        raise RuntimeError("Instagram media container did not return an id")

    last = {}
    for _ in range(POLL_ATTEMPTS):
        status = requests.get(
            f"{GRAPH}/{creation_id}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        )
        last = _response_json(status)
        status_code = str(last.get("status_code", "")).upper()
        if status_code == "FINISHED":
            break
        if status_code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram container failed: {json.dumps(last, ensure_ascii=False)}")
        time.sleep(POLL_SECONDS)
    else:
        raise RuntimeError(f"Instagram container did not finish processing: {json.dumps(last, ensure_ascii=False)}")

    publish = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=60,
    )
    result = _response_json(publish)
    return {
        "creation_id": creation_id,
        "media_id": result.get("id"),
        "processing": last,
        "thumb_offset_ms": max(0, IG_THUMB_OFFSET_MS),
    }


def publish_facebook_reel(video_path: Path, caption: str) -> dict:
    token = _required("META_PAGE_ACCESS_TOKEN")
    page_identity = validate_page_token()

    # Meta's Page Reels flow uses /me/video_reels with a Page access token.
    # The explicit identity check above guarantees that /me resolves to the
    # configured Facebook Page before we attempt any upload.
    start = requests.post(
        f"{GRAPH}/me/video_reels",
        data={"upload_phase": "start", "access_token": token},
        timeout=60,
    )
    started = _response_json(start)
    video_id = str(started.get("video_id", ""))
    upload_url = str(started.get("upload_url", ""))
    if not video_id or not upload_url:
        raise RuntimeError(f"Facebook Reel start response incomplete: {json.dumps(started, ensure_ascii=False)}")

    size = video_path.stat().st_size
    with video_path.open("rb") as handle:
        upload = requests.post(
            upload_url,
            headers={
                "Authorization": f"OAuth {token}",
                "offset": "0",
                "file_size": str(size),
                "Content-Type": "application/octet-stream",
            },
            data=handle,
            timeout=600,
        )
    uploaded = _response_json(upload)

    finish = requests.post(
        f"{GRAPH}/me/video_reels",
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "description": caption,
            "access_token": token,
        },
        timeout=60,
    )
    finished = _response_json(finish)
    if finished.get("success") is not True:
        raise RuntimeError(f"Facebook Reel finish did not confirm success: {json.dumps(finished, ensure_ascii=False)}")

    return {
        "page": page_identity,
        "video_id": video_id,
        "upload": uploaded,
        "finish": finished,
    }


def publish(video_path: Path, video_id: str, caption: str, platforms: set[str]) -> dict:
    if not video_path.exists() or video_path.stat().st_size < 100_000:
        raise RuntimeError(f"Rendered MP4 missing or too small: {video_path}")

    r2_key, video_url = upload_to_r2(video_path, video_id)
    result = {
        "video_id": video_id,
        "video_path": str(video_path),
        "r2_key": r2_key,
        "caption": caption,
        "platforms": {},
    }

    # Publish Facebook first. If Facebook fails, do not create an Instagram-only post.
    if "facebook" in platforms:
        result["platforms"]["facebook"] = publish_facebook_reel(video_path, caption)
    if "instagram" in platforms:
        result["platforms"]["instagram"] = publish_instagram_reel(video_url, caption)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--caption-file", required=True)
    parser.add_argument("--platforms", default="instagram,facebook")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    platforms = {p.strip().lower() for p in args.platforms.split(",") if p.strip()}
    invalid = platforms - {"instagram", "facebook"}
    if invalid or not platforms:
        raise SystemExit(f"Invalid platforms: {sorted(invalid)}")

    caption = Path(args.caption_file).read_text(encoding="utf-8").strip()
    result = publish(Path(args.video), args.video_id, caption, platforms)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
