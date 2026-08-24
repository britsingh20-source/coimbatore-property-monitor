from __future__ import annotations

import json
from pathlib import Path
import subprocess

import cv2
import requests


def _telegram_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No response body"
    return str(body.get("description") or body)[:500]


def extract_reference_frames(job: dict, output_dir: Path, target_count: int = 5) -> list[Path]:
    """Download a source tour and select sharp, low-face-count frames across its timeline."""
    source_url = str(job.get("source_url") or "").strip()
    if not source_url.startswith(("https://www.youtube.com/", "https://youtu.be/")):
        raise RuntimeError("The property job has no supported YouTube source URL")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "source.%(ext)s")
    base_command = [
        "yt-dlp",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        "--socket-timeout",
        "30",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "-f",
        "best[ext=mp4][height<=720]/best[height<=720]/best",
        "-o",
        output_template,
    ]
    client_variants = (
        None,
        "youtube:player_client=web_safari",
        "youtube:player_client=android_vr",
    )
    errors: list[str] = []
    for extractor_args in client_variants:
        for stale in output_dir.glob("source.*"):
            stale.unlink(missing_ok=True)
        command = list(base_command)
        if extractor_args:
            command.extend(["--extractor-args", extractor_args])
        command.append(source_url)
        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=240,
            )
            if list(output_dir.glob("source.*")):
                break
        except subprocess.TimeoutExpired:
            errors.append(f"{extractor_args or 'default'}: timed out")
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip().splitlines()
            errors.append(
                f"{extractor_args or 'default'}: "
                f"{(detail[-1] if detail else 'unknown yt-dlp error')[:300]}"
            )
    else:
        raise RuntimeError("YouTube reference download failed after client fallbacks: " + " | ".join(errors)[-900:])

    sources = sorted(output_dir.glob("source.*"))
    if not sources:
        raise RuntimeError("yt-dlp completed but no source video was created")

    capture = cv2.VideoCapture(str(sources[0]))
    if not capture.isOpened():
        raise RuntimeError("OpenCV could not open the downloaded source video")

    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < target_count:
        capture.release()
        raise RuntimeError("Downloaded source video contains too few readable frames")

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    selected: list[Path] = []
    try:
        for group in range(target_count):
            candidates: list[tuple[int, float, object]] = []
            for offset in (0.20, 0.50, 0.80):
                fraction = (group + offset) / target_count
                frame_number = min(total_frames - 1, max(0, int(total_frames * fraction)))
                capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue

                height, width = frame.shape[:2]
                scale = min(1.0, 720.0 / max(width, 1))
                if scale < 1.0:
                    frame = cv2.resize(
                        frame,
                        (int(width * scale), int(height * scale)),
                        interpolation=cv2.INTER_AREA,
                    )
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(
                    gray,
                    scaleFactor=1.15,
                    minNeighbors=5,
                    minSize=(40, 40),
                )
                sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                candidates.append((len(faces), -sharpness, frame))

            if not candidates:
                continue
            candidates.sort(key=lambda item: (item[0], item[1]))
            chosen = candidates[0][2]
            path = output_dir / f"reference-{group + 1}.jpg"
            if cv2.imwrite(str(path), chosen, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
                selected.append(path)
    finally:
        capture.release()

    if len(selected) < 3:
        raise RuntimeError(f"Only {len(selected)} usable reference frames could be extracted")
    return selected


def send_reference_frames(
    frame_paths: list[Path],
    bot_token: str,
    chat_id: str,
    video_id: str,
) -> None:
    """Send 3-5 references as one Telegram album."""
    media = []
    files = {}
    handles = []
    try:
        for index, path in enumerate(frame_paths[:5]):
            key = f"frame{index}"
            handle = path.open("rb")
            handles.append(handle)
            files[key] = (path.name, handle, "image/jpeg")
            item = {"type": "photo", "media": f"attach://{key}"}
            if index == 0:
                item.update(
                    {
                        "caption": (
                            "<b>Property reference frames</b>\n"
                            f"<b>VIDEO_ID:</b> <code>{video_id}</code>\n\n"
                            "Save all five images. In Gemini → Videos, attach them together "
                            "before pasting the prompt file."
                        ),
                        "parse_mode": "HTML",
                    }
                )
            media.append(item)

        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMediaGroup",
            data={"chat_id": chat_id, "media": json.dumps(media)},
            files=files,
            timeout=90,
        )
    finally:
        for handle in handles:
            handle.close()

    if not response.ok:
        raise RuntimeError(
            f"Telegram sendMediaGroup failed (HTTP {response.status_code}): "
            f"{_telegram_error(response)}"
        )
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram rejected reference frames: {_telegram_error(response)}")
