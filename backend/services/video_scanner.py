import json
import re
import subprocess
from pathlib import Path

_EPISODE_RE = re.compile(r"^Episode (\d+) - (.+)$")
_LANGS = ["en", "fr", "uk", "zh"]


def parse_episode_folder(folder_name: str) -> tuple[int, str, str] | None:
    m = _EPISODE_RE.match(folder_name)
    if not m:
        return None
    num = int(m.group(1))
    name = m.group(2)
    slug = f"episode-{num}-{name.lower().replace(' ', '-')}"
    return num, name, slug


def detect_languages(episode_dir: Path) -> list[str]:
    output_dir = episode_dir / "output"
    if not output_dir.is_dir():
        return []
    found = []
    for lang in _LANGS:
        lang_dir = output_dir / lang
        if lang_dir.is_dir() and any(lang_dir.glob("*_FULL.mp4")):
            found.append(lang)
    return found


def _primary_video(episode_dir: Path) -> Path | None:
    en_dir = episode_dir / "output" / "en"
    if en_dir.is_dir():
        matches = list(en_dir.glob("*_FULL.mp4"))
        if matches:
            return matches[0]
    return None


def _extract_metadata(video: Path) -> tuple[float | None, int | None]:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None, None
    fmt = json.loads(result.stdout).get("format", {})
    duration = float(fmt["duration"]) if "duration" in fmt else None
    size = int(fmt["size"]) if "size" in fmt else None
    return duration, size


def _extract_thumbnail(video: Path, thumb: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-i", str(video), "-ss", "00:00:01", "-vframes", "1",
         "-q:v", "2", str(thumb), "-y"],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def scan_episodes(repo_path: Path, thumbs_dir: Path) -> list[dict]:
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    episodes = []

    for entry in sorted(repo_path.iterdir()):
        if not entry.is_dir():
            continue
        parsed = parse_episode_folder(entry.name)
        if parsed is None:
            continue
        episode_num, name, slug = parsed

        primary = _primary_video(entry)
        duration, size, thumb_path = None, None, None

        if primary and primary.exists():
            duration, size = _extract_metadata(primary)
            thumb_file = thumbs_dir / f"{slug}.jpg"
            if _extract_thumbnail(primary, thumb_file):
                thumb_path = f"/thumbs/{slug}.jpg"

        episodes.append({
            "episode_num": episode_num,
            "name": name,
            "slug": slug,
            "folder_path": str(entry),
            "primary_file": str(primary) if primary else None,
            "duration_secs": duration,
            "size_bytes": size,
            "thumbnail_path": thumb_path,
            "languages": detect_languages(entry),
            "has_captions": (entry / "captions.json").exists(),
            "status": "new",
        })

    episodes.sort(key=lambda e: e["episode_num"])
    return episodes
