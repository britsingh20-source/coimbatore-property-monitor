import json
import math
import subprocess
from pathlib import Path


ASSETS = Path("assets/properties")
AUDIO = Path("assets/audio")
OUTPUTS = Path("outputs")
SECONDS_PER_IMAGE = 6
FPS = 30


def property_images(video_id: str) -> list[Path]:
    folder = ASSETS / video_id
    images = []
    for extension in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        images.extend(folder.glob(extension))
    return sorted(images)


def caption_lines(job: dict, image_count: int) -> list[str]:
    location = job.get("property_location") or "Coimbatore"
    facts = [item.strip() for item in job.get("verified_facts", "").split(",") if item.strip()]
    lines = [f"Property near {location}"] + facts
    lines.append(job.get("disclosure", "Property visuals supplied by the advertiser."))
    while len(lines) < image_count:
        lines.append("Contact SB Builders for verified property details")
    return lines[:image_count]


def _timestamp(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},000"


def write_srt(path: Path, lines: list[str], seconds_per_image: int = SECONDS_PER_IMAGE) -> None:
    blocks = []
    for index, line in enumerate(lines, start=1):
        start = (index - 1) * seconds_per_image
        end = index * seconds_per_image
        blocks.append(
            f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{line}\n"
        )
    path.write_text("\n".join(blocks), encoding="utf-8")


def render_job(job_path: Path) -> Path:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    video_id = job["video_id"]
    images = property_images(video_id)
    if len(images) < 3:
        raise FileNotFoundError(
            f"Add at least 3 owned images to assets/properties/{video_id}/"
        )

    output_dir = OUTPUTS / video_id
    output_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    audio = next((path for path in [AUDIO / f"{video_id}.mp3", AUDIO / f"{video_id}.wav"] if path.exists()), None)
    seconds_per_image = SECONDS_PER_IMAGE
    if audio:
        probe = subprocess.run([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio),
        ], check=True, capture_output=True, text=True)
        audio_seconds = float(probe.stdout.strip())
        seconds_per_image = max(SECONDS_PER_IMAGE, math.ceil(audio_seconds / len(images)) + 1)
    frames = seconds_per_image * FPS

    for index, image in enumerate(images, start=1):
        clip = output_dir / f"{index:02d}.mp4"
        zoom = "min(zoom+0.0005,1.08)" if index % 2 else "if(lte(zoom,1.0),1.08,max(1.0,zoom-0.0005))"
        filter_graph = (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"zoompan=z='{zoom}':d={frames}:s=1080x1920:fps={FPS},"
            "fade=t=in:st=0:d=0.5,"
            f"fade=t=out:st={seconds_per_image - 0.5}:d=0.5,format=yuv420p"
        )
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(image),
            "-vf", filter_graph, "-t", str(seconds_per_image), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", str(clip),
        ], check=True)
        clips.append(clip)

    concat_file = output_dir / "clips.txt"
    concat_file.write_text(
        "".join(f"file '{clip.resolve()}'\n" for clip in clips), encoding="utf-8"
    )
    joined = output_dir / "joined.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(joined),
    ], check=True)

    captions = output_dir / "captions.srt"
    write_srt(captions, caption_lines(job, len(images)), seconds_per_image)
    final = output_dir / "final-free-vertical.mp4"
    command = ["ffmpeg", "-y", "-i", str(joined)]
    if audio:
        command += ["-stream_loop", "-1", "-i", str(audio)]
    command += [
        "-vf", f"subtitles={captions}:force_style='FontName=Noto Sans Tamil,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Alignment=2,MarginV=120'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
    ]
    if audio:
        command += ["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k", "-shortest"]
    else:
        command += ["-an"]
    command.append(str(final))
    subprocess.run(command, check=True)
    return final
