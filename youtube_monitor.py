import json
import os

import requests


YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

# Default: check the latest 5 uploads from each channel.
# You can override this in GitHub Actions using:
# RECENT_UPLOADS: "10"
RECENT_UPLOADS = int(
    os.environ.get(
        "RECENT_UPLOADS",
        "5"
    )
)


def get_channel(handle: str) -> dict:
    """
    Resolve a YouTube @handle and return the channel ID,
    channel title and uploads playlist ID.
    """

    params = {
        "part": "id,snippet,contentDetails",
        "forHandle": handle,
        "key": os.environ["YOUTUBE_API_KEY"]
    }

    response = requests.get(
        f"{YOUTUBE_API}/channels",
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    if not items:
        raise RuntimeError(
            f"Channel not found for handle: {handle}"
        )

    channel = items[0]

    uploads_playlist = (
        channel
        .get("contentDetails", {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )

    if not uploads_playlist:
        raise RuntimeError(
            f"Uploads playlist not found for handle: {handle}"
        )

    return {
        "channel_id": channel["id"],
        "channel_title": channel["snippet"]["title"],
        "uploads_playlist": uploads_playlist
    }


def get_recent_videos(
    uploads_playlist: str,
    max_results: int = RECENT_UPLOADS
) -> list[dict]:
    """
    Retrieve recent uploads from a channel uploads playlist.
    """

    safe_max_results = max(
        1,
        min(50, max_results)
    )

    params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": safe_max_results,
        "key": os.environ["YOUTUBE_API_KEY"]
    }

    response = requests.get(
        f"{YOUTUBE_API}/playlistItems",
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()
    items = data.get("items", [])

    videos = []

    for item in items:
        snippet = item.get("snippet", {})
        content_details = item.get(
            "contentDetails",
            {}
        )

        video_id = content_details.get("videoId")

        if not video_id:
            print(
                "Skipping playlist item without video ID."
            )
            continue

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = ""

        for size in [
            "maxres",
            "standard",
            "high",
            "medium",
            "default"
        ]:
            if size in thumbnails:
                thumbnail = thumbnails[size].get(
                    "url",
                    ""
                )
                break

        videos.append({
            "video_id": video_id,
            "title": snippet.get(
                "title",
                "UNTITLED"
            ),
            "description": snippet.get(
                "description",
                ""
            ),
            "published_at": snippet.get(
                "publishedAt",
                ""
            ),
            "channel_title": snippet.get(
                "channelTitle",
                ""
            ),
            "thumbnail": thumbnail,
            "url": (
                "https://www.youtube.com/watch"
                f"?v={video_id}"
            )
        })

    videos.sort(
        key=lambda video: video.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    return videos[:safe_max_results]


def main() -> list[dict]:
    """
    Check every configured channel and return recent videos.
    One failed channel will not stop the others.
    """

    config_path = "config/channels.json"

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Channel config not found: {config_path}"
        )

    with open(
        config_path,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(file)

    channels = config.get("channels", [])

    if not channels:
        raise RuntimeError(
            "No channels found in config/channels.json"
        )

    results = []
    seen_video_ids = set()

    for channel in channels:
        channel_name = channel.get(
            "name",
            "UNKNOWN CHANNEL"
        )

        handle = channel.get("handle")

        if not handle:
            print(
                f"ERROR - {channel_name}: "
                "missing YouTube handle"
            )
            continue

        try:
            channel_info = get_channel(handle)

            videos = get_recent_videos(
                channel_info["uploads_playlist"],
                RECENT_UPLOADS
            )

            added_count = 0

            for video in videos:
                video_id = video["video_id"]

                # Prevent duplicates inside the same run.
                if video_id in seen_video_ids:
                    continue

                seen_video_ids.add(video_id)

                video["source_name"] = channel_name
                video["source_handle"] = handle
                video["channel_id"] = (
                    channel_info["channel_id"]
                )

                results.append(video)
                added_count += 1

            print(
                f"{channel_name}: found "
                f"{len(videos)} recent upload(s), "
                f"added {added_count}"
            )

        except requests.HTTPError as error:
            status_code = (
                error.response.status_code
                if error.response is not None
                else "unknown"
            )

            print(
                f"ERROR - {channel_name}: "
                f"YouTube API HTTP {status_code} - "
                f"{error}"
            )

        except requests.RequestException as error:
            print(
                f"ERROR - {channel_name}: "
                f"network/API request failed - "
                f"{error}"
            )

        except Exception as error:
            print(
                f"ERROR - {channel_name}: "
                f"{error}"
            )

    results.sort(
        key=lambda video: video.get(
            "published_at",
            ""
        ),
        reverse=True
    )

    print(
        f"Total recent videos collected: "
        f"{len(results)}"
    )

    return results


if __name__ == "__main__":
    videos = main()

    for video in videos:
        print(
            f"{video['source_name']} | "
            f"{video['published_at']} | "
            f"{video['title']} | "
            f"{video['url']}"
        )
