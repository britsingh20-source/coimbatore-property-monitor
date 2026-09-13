import json
import os

import requests


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
RECENT_UPLOADS = int(os.environ.get("RECENT_UPLOADS", "5"))


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


def main() -> list[dict]:
    """Scan the configured trusted channels exactly as the original monitor did."""
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

    results.sort(key=lambda video: video.get("published_at", ""), reverse=True)
    print(f"Total recent videos collected: {len(results)}")
    return results


if __name__ == "__main__":
    for video in main():
        print(
            f"{video.get('source_name', '')} | {video.get('source_type', '')} | "
            f"{video['published_at']} | {video['title']} | {video['url']}"
        )
