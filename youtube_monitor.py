import json
import os
import requests

YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


def get_channel(handle):
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

    items = response.json().get("items", [])

    if not items:
        raise RuntimeError(f"Channel not found: {handle}")

    channel = items[0]

    return {
        "channel_id": channel["id"],
        "channel_title": channel["snippet"]["title"],
        "uploads_playlist": channel["contentDetails"]["relatedPlaylists"]["uploads"]
    }


RECENT_UPLOADS = int(os.environ.get("RECENT_UPLOADS", "20"))


def get_recent_videos(uploads_playlist, max_results=RECENT_UPLOADS):
    params = {
        "part": "snippet,contentDetails",
        "playlistId": uploads_playlist,
        "maxResults": min(50, max_results),
        "key": os.environ["YOUTUBE_API_KEY"]
    }

    response = requests.get(
        f"{YOUTUBE_API}/playlistItems",
        params=params,
        timeout=30
    )
    response.raise_for_status()

    items = response.json().get("items", [])

    if not items:
        return []

    videos = []

    for item in items:
        snippet = item["snippet"]
        video_id = item["contentDetails"]["videoId"]

        videos.append({
            "video_id": video_id,
            "title": snippet["title"],
            "description": snippet.get("description", ""),
            "published_at": snippet["publishedAt"],
            "channel_title": snippet["channelTitle"],
            "thumbnail": snippet["thumbnails"]["high"]["url"],
            "url": f"https://www.youtube.com/watch?v={video_id}"
        })

    videos.sort(
        key=lambda x: x["published_at"],
        reverse=True
    )

    return videos[:max_results]


def main():

    with open("config/channels.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    results = []

    for channel in config["channels"]:

        try:
            channel_info = get_channel(channel["handle"])

            videos = get_recent_videos(
                channel_info["uploads_playlist"]
            )

            for video in videos:
                video["source_name"] = channel["name"]
                results.append(video)

            print(
                f'{channel["name"]}: '
                f'found {len(videos)} recent upload(s)'
            )

        except Exception as e:
            print(
                f'ERROR - {channel["name"]}: {e}'
            )

    return results


if __name__ == "__main__":
    main()
