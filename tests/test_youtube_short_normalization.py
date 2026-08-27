from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from r2_social_autopilot import prepare_youtube_short


@patch("r2_social_autopilot.subprocess.run")
@patch("r2_social_autopilot._probe_video")
def test_landscape_video_gets_portrait_blurred_fill(probe, run, tmp_path):
    probe.side_effect = [
        {"width": 1920, "height": 1080, "duration": 30.0},
        {"width": 1080, "height": 1920, "duration": 30.0},
    ]
    source = Path("landscape.mp4")
    output = tmp_path / "short.mp4"

    result = prepare_youtube_short(source, output)

    assert result["layout"] == "landscape_blurred_fill"
    command = run.call_args.args[0]
    assert "boxblur=24:2" in command[command.index("-filter_complex") + 1]
    assert command[-1] == str(output)


@patch("r2_social_autopilot.subprocess.run")
@patch("r2_social_autopilot._probe_video")
def test_portrait_video_is_still_normalized_to_exact_short_dimensions(probe, run, tmp_path):
    probe.side_effect = [
        {"width": 720, "height": 1280, "duration": 10.0},
        {"width": 1080, "height": 1920, "duration": 10.0},
    ]

    result = prepare_youtube_short(Path("portrait.mp4"), tmp_path / "short.mp4")

    assert result["layout"] == "portrait_crop"
    command = run.call_args.args[0]
    assert "crop=1080:1920" in command[command.index("-filter_complex") + 1]


@patch("r2_social_autopilot._probe_video")
def test_video_over_three_minutes_is_rejected(probe, tmp_path):
    probe.return_value = {"width": 1080, "height": 1920, "duration": 181.0}

    with TestCase().assertRaisesRegex(RuntimeError, "no longer than 180s"):
        prepare_youtube_short(Path("long.mp4"), tmp_path / "short.mp4")
