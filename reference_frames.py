from __future__ import annotations

import json
from pathlib import Path
import subprocess
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
import requests


def _telegram_error(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text.strip()[:500] or "No response body"
    return str(body.get("description") or body)[:500]


def _youtube_video_id(source_url: str) -> str:
    parsed = urlparse(source_url)
    if parsed.netloc.endswith("youtu.be"):
        return parsed.path.strip("/").split("/")[0]
    return parse_qs(parsed.query).get("v", [""])[0]


def _storyboard_reference_frames(
    source_url: str,
    output_dir: Path,
    target_count: int,
) -> list[Path]:
    """Use YouTube's public time-sampled storyboard sheets when video delivery is blocked."""
    video_id = _youtube_video_id(source_url)
    if not video_id:
        raise RuntimeError("Could not parse the YouTube video ID for storyboard fallback")

    cells: list[object] = []
    for level in ("L2", "L1", "L0"):
        level_cells: list[object] = []
        misses = 0
        for sheet_number in range(20):
            url = (
                f"https://i.ytimg.com/sb/{video_id}/"
                f"storyboard3_{level}/M{sheet_number}.jpg"
            )
            try:
                response = requests.get(url, timeout=30)
            except requests.RequestException:
                misses += 1
                if misses >= 2:
                    break
                continue
            if response.status_code != 200 or not response.content:
                misses += 1
                if misses >= 2:
                    break
                continue

            sheet = cv2.imdecode(
                np.frombuffer(response.content, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if sheet is None:
                continue
            height, width = sheet.shape[:2]
            grid_options = (5, 10)
            grid = min(
                grid_options,
                key=lambda value: abs((width / value) / max(height / value, 1) - 16 / 9),
            )
            cell_width = width // grid
            cell_height = height // grid
            for row in range(grid):
                for column in range(grid):
                    crop = sheet[
                        row * cell_height : (row + 1) * cell_height,
                        column * cell_width : (column + 1) * cell_width,
                    ]
                    if crop.size and float(crop.mean()) > 4.0:
                        level_cells.append(crop.copy())
            misses = 0
        if len(level_cells) >= target_count:
            cells = level_cells
            break

    if len(cells) < target_count:
        raise RuntimeError("YouTube storyboard images were unavailable")

    face_detector = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    selected: list[Path] = []
    for group in range(target_count):
        start = int(len(cells) * group / target_count)
        end = max(start + 1, int(len(cells) * (group + 1) / target_count))
        candidates = []
        for frame in cells[start:end]:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(
                gray,
                scaleFactor=1.15,
                minNeighbors=5,
                minSize=(24, 24),
            )
            sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            candidates.append((len(faces), -sharpness, frame))
        candidates.sort(key=lambda item: (item[0], item[1]))
        chosen = candidates[0][2]
        enlarged = cv2.resize(chosen, (720, 405), interpolation=cv2.INTER_CUBIC)
        path = output_dir / f"reference-{group + 1}.jpg"
        if cv2.imwrite(str(path), enlarged, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
            selected.append(path)

    if len(selected) != target_count:
        raise RuntimeError(f"Storyboard fallback produced only {len(selected)} frames")
    return selected


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
        try:
            return _storyboard_reference_frames(source_url, output_dir, target_count)
        except Exception as storyboard_exc:
            errors.append(f"storyboard: {storyboard_exc}")
            raise RuntimeError(
                "YouTube video and storyboard extraction both failed: "
                + " | ".join(errors)[-900:]
            ) from storyboard_exc

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
