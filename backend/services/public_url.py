import re
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

_TUNNEL_URL_RE = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


@contextmanager
def public_url_context(video_path: Path, episode_id: int, settings) -> Generator[str, None, None]:
    """Yield a public HTTPS URL for the given video, cleaning up on exit."""
    if settings.ig_public_url_mode == "r2":
        with _r2_context(video_path, episode_id, settings) as url:
            yield url
    else:
        with _tunnel_context(video_path, episode_id) as url:
            yield url


@contextmanager
def _tunnel_context(video_path: Path, episode_id: int) -> Generator[str, None, None]:
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        tunnel_url = None
        for line in proc.stderr:
            match = _TUNNEL_URL_RE.search(line)
            if match:
                tunnel_url = match.group(0)
                break
        if not tunnel_url:
            raise RuntimeError("Cloudflare tunnel did not return a URL")
        yield f"{tunnel_url}/media/{episode_id}.mp4"
    finally:
        proc.terminate()
        proc.wait()


@contextmanager
def _r2_context(video_path: Path, episode_id: int, settings) -> Generator[str, None, None]:
    raise NotImplementedError("R2 mode is not yet implemented")
