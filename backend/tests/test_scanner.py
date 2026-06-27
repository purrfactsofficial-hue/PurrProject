from pathlib import Path
from unittest.mock import MagicMock, patch

from services.video_scanner import detect_languages, parse_episode_folder, scan_episodes

# ---------------------------------------------------------------------------
# parse_episode_folder
# ---------------------------------------------------------------------------


def test_parse_episode_folder_single_word():
    result = parse_episode_folder("Episode 9 - Pizza")
    assert result == (9, "Pizza", "episode-9-pizza")


def test_parse_episode_folder_multi_word():
    result = parse_episode_folder("Episode 12 - Great Wall")
    assert result == (12, "Great Wall", "episode-12-great-wall")


def test_parse_episode_folder_large_number():
    result = parse_episode_folder("Episode 19 - Cosmos")
    assert result == (19, "Cosmos", "episode-19-cosmos")


def test_parse_episode_folder_returns_none_for_common_parts():
    assert parse_episode_folder("Common parts") is None


def test_parse_episode_folder_returns_none_for_unrecognised():
    assert parse_episode_folder("random folder") is None


# ---------------------------------------------------------------------------
# detect_languages
# ---------------------------------------------------------------------------


def test_detect_languages_finds_all_four(tmp_path):
    for lang in ["en", "fr", "uk", "zh"]:
        d = tmp_path / "output" / lang
        d.mkdir(parents=True)
        (d / "Episode_9___Pizza_FULL.mp4").touch()
    assert sorted(detect_languages(tmp_path)) == ["en", "fr", "uk", "zh"]


def test_detect_languages_partial(tmp_path):
    for lang in ["en", "fr"]:
        d = tmp_path / "output" / lang
        d.mkdir(parents=True)
        (d / "Episode_9___Pizza_FULL.mp4").touch()
    assert sorted(detect_languages(tmp_path)) == ["en", "fr"]


def test_detect_languages_dir_exists_but_no_full_mp4(tmp_path):
    d = tmp_path / "output" / "en"
    d.mkdir(parents=True)
    (d / "scene1_FINAL.mp4").touch()  # not a FULL file
    assert detect_languages(tmp_path) == []


def test_detect_languages_no_output_dir(tmp_path):
    assert detect_languages(tmp_path) == []


# ---------------------------------------------------------------------------
# scan_episodes — integration-style with mocked subprocess
# ---------------------------------------------------------------------------

FAKE_FFPROBE = MagicMock(
    returncode=0, stdout='{"format":{"duration":"44.5","size":"17600000"}}', stderr=""
)
FAKE_FFMPEG = MagicMock(returncode=0, stdout="", stderr="")


def _make_ep(root: Path, folder: str, langs: list[str]) -> None:
    ep = root / folder
    ep.mkdir()
    for lang in langs:
        d = ep / "output" / lang
        d.mkdir(parents=True)
        slug = folder.replace(" - ", "___").replace(" ", "_")
        (d / f"{slug}_FULL.mp4").touch()


@patch("services.video_scanner.subprocess.run")
def test_scan_finds_episode(mock_run, tmp_path):
    mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en", "fr", "uk", "zh"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)

    assert len(results) == 1
    ep = results[0]
    assert ep["episode_num"] == 9
    assert ep["name"] == "Pizza"
    assert ep["slug"] == "episode-9-pizza"
    assert sorted(ep["languages"]) == ["en", "fr", "uk", "zh"]
    assert ep["duration_secs"] == 44.5
    assert ep["size_bytes"] == 17_600_000
    assert ep["status"] == "new"


@patch("services.video_scanner.subprocess.run")
def test_scan_skips_common_parts(mock_run, tmp_path):
    mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    (tmp_path / "Common parts").mkdir()
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)
    assert len(results) == 1
    assert results[0]["name"] == "Pizza"


@patch("services.video_scanner.subprocess.run")
def test_scan_sorted_by_episode_num(mock_run, tmp_path):
    mock_run.side_effect = [
        FAKE_FFPROBE,
        FAKE_FFMPEG,
        FAKE_FFPROBE,
        FAKE_FFMPEG,
    ]
    _make_ep(tmp_path, "Episode 19 - Cosmos", ["en"])
    _make_ep(tmp_path, "Episode 2 - Venus", ["en"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()

    results = scan_episodes(tmp_path, thumbs)
    assert results[0]["episode_num"] == 2
    assert results[1]["episode_num"] == 19


def test_scan_detects_captions_json_present(tmp_path):
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    (tmp_path / "Episode 9 - Pizza" / "captions.json").write_text("{}", encoding="utf-8")
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
        results = scan_episodes(tmp_path, thumbs)
    assert results[0]["has_captions"] is True


def test_scan_detects_captions_json_absent(tmp_path):
    _make_ep(tmp_path, "Episode 9 - Pizza", ["en"])
    thumbs = tmp_path / "thumbs"
    thumbs.mkdir()
    with patch("services.video_scanner.subprocess.run") as mock_run:
        mock_run.side_effect = [FAKE_FFPROBE, FAKE_FFMPEG]
        results = scan_episodes(tmp_path, thumbs)
    assert results[0]["has_captions"] is False
