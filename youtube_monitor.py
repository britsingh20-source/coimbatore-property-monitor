import json
import os
from datetime import datetime, timezone

import requests

from location_matcher import active_weekly_focus, normalize


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

# Default: check the latest 5 uploads from each trusted channel.
RECENT_UPLOADS = int(os.environ.get("RECENT_UPLOADS", "5"))
FOCUS_DISCOVERY_RESULTS = int(os.environ.get("FOCUS_DISCOVERY_RESULTS", "10"))


def get_channel(handle: str) -> dict:
    params = {
        "part": "id,snippet,contentDetails",
        "forHandle": handle,
        "key": os.environ["YOUTUBE_API_KEY"],
    }
    response = requests.get(f"{YOUTUBE_API}/channels", params=params, timeout=30)
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        raise RuntimeError(f"Channel not found for handle: {handle}")

    channel = items[0]
    uploads_playlist = (
        channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
    )
    if not uploads_playlist:
        raise RuntimeError(f"Uploads playlist not found for handle: {handle}")

    return {
        "channel_id": channel["id"],
        "channel_title": channel["snippet"]["title"],
        "uploads_playlist": uploads_playlist,
    }


def _thumbnail(snippet: dict) -> str:
    thumbnails = snippet.get("thumbnails", {})
    for size in ["maxres", "standard", "high", "medium", "default"]:
        if size in thumbnails:
            return thumbnails[size].get("url", "")
    return ""


def get_recent_videos(uploads_playlist: str, max_results: int = RECENT_UPLOADS) -> list[dict]:
    safe_max_results = max(1, min(50, max_results))
    params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": safe_max_results,
        "key": os.environ["YOUTUBE_API_KEY"],
    }
    response = requests.get(f"{YOUTUBE_API}/playlistItems", params=params, timeout=30)
    response.raise_for_status()

    videos = []
    for item in response.json().get("items", []):
        snippet = item.get("snippet", {})
        video_id = item.get("contentDetails", {}).get("videoId")
        if not video_id:
            continue
        videos.append({
            "video_id": video_id,
            "title": snippet.get("title", "UNTITLED"),
            "description": snippet.get("description", ""),
            "published_at": snippet.get("publishedAt", ""),
            "channel_title": snippet.get("channelTitle", ""),
            "thumbnail": _thumbnail(snippet),
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "source_type": "trusted_channel",
        })

    videos.sort(key=lambda video: video.get("published_at", ""), reverse=True)
    return videos[:safe_max_results]


def _focus_terms(focus: dict) -> list[str]:
    terms = []
    normalized_seen = set()
    for area in focus.get("focus_areas", []):
        for value in [area.get("name"), *(area.get("aliases") or []), *(area.get("micro_localities") or [])]:
            value = str(value or "").strip()
            normalized = normalize(value)
            if value and normalized and normalized not in normalized_seen:
                terms.append(value)
                normalized_seen.add(normalized)
    return terms


def _metadata_has_focus(video: dict, focus: dict) -> bool:
    text = normalize(f"{video.get('title', '')} {video.get('description', '')}")
    return any(normalize(term) in text for term in _focus_terms(focus) if normalize(term))


def _published_after(focus: dict) -> str | None:
    start = str(focus.get("week_start") or "").strip()
    if not start:
        return None
    try:
        dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        return dt.isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def _published_in_focus_week(video: dict, focus: dict) -> bool:
    start = str(focus.get("week_start") or "").strip()
    end = str(focus.get("week_end") or "").strip()
    published = str(video.get("published_at") or "").strip()
    if not start or not published:
        return False
    try:
        published_date = datetime.fromisoformat(published.replace("Z", "+00:00")).date()
        start_date = datetime.fromisoformat(start).date()
        if end:
            end_date = datetime.fromisoformat(end).date()
            return start_date <= published_date <= end_date
        return published_date >= start_date
    except ValueError:
        return False


def _focus_query(area: dict) -> str:
    # YouTube search supports | as OR. One query per selected focus area keeps
    # quota bounded while covering the main locality plus several saved pockets.
    raw_terms = [area.get("name"), *(area.get("micro_localities") or [])[:3]]
    terms = []
    for value in raw_terms:
        value = str(value or "").strip()
        if value and value.casefold() not in {item.casefold() for item in terms}:
            terms.append(value)
    locality = "|".join(terms) if terms else str(area.get("name") or "Coimbatore")
    return f"{locality} property house villa plot for sale Coimbatore"


def discover_focus_videos(focus: dict, seen_video_ids: set[str]) -> list[dict]:
    """Search public YouTube beyond the trusted channel list for active focus areas."""
    results = []
    max_results = max(1, min(25, FOCUS_DISCOVERY_RESULTS))
    published_after = _published_after(focus)

    for area in focus.get("focus_areas", [])[:2]:
        query = _focus_query(area)
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "date",
            "maxResults": max_results,
            "key": os.environ["YOUTUBE_API_KEY"],
        }
        if published_after:
            params["publishedAfter"] = published_after

        try:
            response = requests.get(f"{YOUTUBE_API}/search", params=params, timeout=30)
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"FOCUS DISCOVERY ERROR - {area.get('name', 'unknown')}: {error}")
            continue

        found = 0
        accepted = 0
        for item in response.json().get("items", []):
            found += 1
            video_id = item.get("id", {}).get("videoId")
            snippet = item.get("snippet", {})
            if not video_id or video_id in seen_video_ids:
                continue
            video = {
                "video_id": video_id,
                "title": snippet.get("title", "UNTITLED"),
                "description": snippet.get("description", ""),
                "published_at": snippet.get("publishedAt", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "thumbnail": _thumbnail(snippet),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "source_name": snippet.get("channelTitle", "YouTube focus discovery"),
                "source_handle": "",
                "channel_id": snippet.get("channelId", ""),
                "source_type": "weekly_focus_discovery",
                "discovery_focus_area": area.get("name", ""),
                "discovery_query": query,
            }
            # Search relevance is not enough. Require the selected area or one
            # of its configured micro-localities in metadata before spending a
            # Gemini call; Gemini/location_matcher performs final verification.
            if not _metadata_has_focus(video, {"focus_areas": [area]}):
                continue
            seen_video_ids.add(video_id)
            results.append(video)
            accepted += 1
        print(
            f"Focus discovery {area.get('name', 'unknown')}: search returned {found}, "
            f"accepted {accepted} metadata-matching video(s)"
        )

    results.sort(key=lambda video: video.get("published_at", ""), reverse=True)
    return results


def main() -> list[dict]:
    """
    Stage 1: scan the configured trusted channels.
    Stage 2: if those channels have no upload THIS WEEK matching the active
    focus, search public YouTube for that focus area and saved micro-localities.
    """
    config_path = "config/channels.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Channel config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        channels = json.load(file).get("channels", [])
    if not channels:
        raise RuntimeError("No channels found in config/channels.json")

    results = []
    seen_video_ids = set()

    for channel in channels:
        channel_name = channel.get("name", "UNKNOWN CHANNEL")
        handle = channel.get("handle")
        if not handle:
            print(f"ERROR - {channel_name}: missing YouTube handle")
            continue
        try:
            channel_info = get_channel(handle)
            videos = get_recent_videos(channel_info["uploads_playlist"], RECENT_UPLOADS)
            added_count = 0
            for video in videos:
                video_id = video["video_id"]
                if video_id in seen_video_ids:
                    continue
                seen_video_ids.add(video_id)
                video["source_name"] = channel_name
                video["source_handle"] = handle
                video["channel_id"] = channel_info["channel_id"]
                results.append(video)
                added_count += 1
            print(f"{channel_name}: found {len(videos)} recent upload(s), added {added_count}")
        except requests.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else "unknown"
            print(f"ERROR - {channel_name}: YouTube API HTTP {status_code} - {error}")
        except requests.RequestException as error:
            print(f"ERROR - {channel_name}: network/API request failed - {error}")
        except Exception as error:
            print(f"ERROR - {channel_name}: {error}")

    focus = active_weekly_focus()
    if focus:
        trusted_focus_this_week = [
            video for video in results
            if _metadata_has_focus(video, focus) and _published_in_focus_week(video, focus)
        ]
        focus_names = [str(area.get("name") or "").strip() for area in focus.get("focus_areas", [])]
        print(f"Weekly focus active: {' + '.join(filter(None, focus_names))}")
        print(f"Trusted-channel THIS-WEEK metadata matches for focus: {len(trusted_focus_this_week)}")
        if not trusted_focus_this_week:
            print("No this-week trusted-channel focus upload; starting public YouTube focus discovery.")
            discovered = discover_focus_videos(focus, seen_video_ids)
            results.extend(discovered)
            if not discovered:
                print("No verified-focus metadata candidate found outside the trusted channels in this scan.")
    else:
        print("No active weekly focus; public area discovery skipped.")

    results.sort(key=lambda video: video.get("published_at", ""), reverse=True)
    print(f"Total recent videos collected: {len(results)}")
    return results


if __name__ == "__main__":
    for video in main():
        print(
            f"{video.get('source_name', '')} | {video.get('source_type', '')} | "
            f"{video['published_at']} | {video['title']} | {video['url']}"
        )
