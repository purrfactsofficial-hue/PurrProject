from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_settings(mode="tunnel"):
    s = MagicMock()
    s.ig_public_url_mode = mode
    s.r2_public_base = "https://my-bucket.r2.dev"
    return s


@patch("services.public_url.subprocess.Popen")
def test_tunnel_context_yields_public_url(mock_popen):
    from services.public_url import public_url_context

    proc = MagicMock()
    proc.stderr = iter(
        [
            "Some startup log\n",
            "2024/01/01 Your quick Tunnel https://abc123.trycloudflare.com is ready!\n",
            "Further logs\n",
        ]
    )
    mock_popen.return_value = proc

    with public_url_context(Path("/video.mp4"), 5, _make_settings("tunnel")) as url:
        assert url == "https://abc123.trycloudflare.com/media/5/en.mp4"

    proc.terminate.assert_called_once()
    proc.wait.assert_called_once()


@patch("services.public_url.subprocess.Popen")
def test_tunnel_context_uses_language_in_url(mock_popen):
    from services.public_url import public_url_context

    proc = MagicMock()
    proc.stderr = iter(
        [
            "https://xyz.trycloudflare.com quick Tunnel ready!\n",
        ]
    )
    mock_popen.return_value = proc

    with public_url_context(Path("/video.mp4"), 5, _make_settings("tunnel"), language="fr") as url:
        assert url == "https://xyz.trycloudflare.com/media/5/fr.mp4"


@patch("services.public_url.subprocess.Popen")
def test_tunnel_context_raises_if_no_url(mock_popen):
    from services.public_url import public_url_context

    proc = MagicMock()
    proc.stderr = iter(["startup log\n", "another line\n"])
    mock_popen.return_value = proc

    with (
        pytest.raises(RuntimeError, match="did not return a URL"),
        public_url_context(Path("/video.mp4"), 5, _make_settings("tunnel")),
    ):
        pass  # pragma: no cover


@patch("services.public_url.subprocess.Popen")
def test_tunnel_context_cleans_up_on_exception(mock_popen):
    from services.public_url import public_url_context

    proc = MagicMock()
    proc.stderr = iter(
        [
            "https://xyz.trycloudflare.com ready\n",
        ]
    )
    mock_popen.return_value = proc

    with (
        pytest.raises(ValueError),
        public_url_context(Path("/video.mp4"), 5, _make_settings("tunnel")),
    ):
        raise ValueError("publish failed")

    proc.terminate.assert_called_once()
