"""Mocked unit tests for uncovered branches in services/video_scanner.py.

Lines targeted: 38 (_primary_video returns None), 47 (ffprobe failure), 69 (skip non-dirs).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from services.video_scanner import _extract_metadata, _primary_video, scan_episodes

# ---------------------------------------------------------------------------
# _primary_video returns None  (line 38)
# ---------------------------------------------------------------------------


def test_primary_video_returns_none_when_no_en_dir(tmp_path):
    """_primary_video returns None when output/en/ does not exist."""
    result = _primary_video(tmp_path)
    assert result is None


def test_primary_video_returns_none_when_no_full_mp4(tmp_path):
    """_primary_video returns None when output/en/ exists but has no *_FULL.mp4 file."""
    en_dir = tmp_path / "output" / "en"
    en_dir.mkdir(parents=True)
    (en_dir / "scene1_FINAL.mp4").touch()  # not a FULL file
    result = _primary_video(tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# _extract_metadata with failing ffprobe  (line 47)
# ---------------------------------------------------------------------------


def test_extract_metadata_returns_none_on_ffprobe_failure():
    """_extract_metadata returns (None, None) when ffprobe exits non-zero."""
    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error output")
        duration, size = _extract_metadata(Path("/some/fake/video.mp4"))

    assert duration is None
    assert size is None


# ---------------------------------------------------------------------------
# scan_episodes skips non-directory entries  (line 69)
# ---------------------------------------------------------------------------


def test_scan_episodes_skips_files_not_dirs(tmp_path):
    """scan_episodes skips plain files in the repo path (only processes dirs)."""
    # Plant a file that should be skipped
    (tmp_path / "README.txt").write_text("ignore me")

    # Plant a valid episode directory
    ep = tmp_path / "Episode 9 - Pizza"
    ep.mkdir()
    en = ep / "output" / "en"
    en.mkdir(parents=True)
    (en / "Episode_9___Pizza_FULL.mp4").touch()

    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    fake_probe = MagicMock(
        returncode=0,
        stdout='{"format":{"duration":"44.5","size":"17600000"}}',
        stderr="",
    )
    fake_ffmpeg = MagicMock(returncode=0, stdout="", stderr="")

    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.side_effect = [fake_probe, fake_ffmpeg]
        results = scan_episodes(tmp_path, thumbs)

    # Only the episode directory should appear in results
    assert len(results) == 1
    assert results[0]["name"] == "Pizza"
