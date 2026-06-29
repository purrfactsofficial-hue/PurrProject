from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_caption(body="Wow, cool fact!", hashtags=None):
    cap = MagicMock()
    cap.body = body
    cap.hashtags = hashtags or ["#PurrFacts", "#Shorts", "#Facts"]
    return cap


def _make_settings(lang="en", cookie_file="/cookies/en.json"):
    s = MagicMock()
    setattr(s, f"tiktok_cookies_{lang}", cookie_file)
    return s


@patch("services.tiktok.upload_tiktok")
def test_publish_tiktok_returns_post_ref(mock_upload):
    from services.tiktok import publish_tiktok

    mock_upload.return_value = "tiktok-post-ref-123"

    result = publish_tiktok(_make_caption(), Path("/fake/video.mp4"), _make_settings(), "en")

    assert result == "tiktok-post-ref-123"
    mock_upload.assert_called_once()


@patch("services.tiktok.upload_tiktok")
def test_publish_tiktok_passes_description_and_cookies(mock_upload):
    from services.tiktok import publish_tiktok

    mock_upload.return_value = "ref"
    cap = _make_caption(body="Fun fact", hashtags=["#PurrFacts"])
    publish_tiktok(cap, Path("/v.mp4"), _make_settings("en", "/c/en.json"), "en")

    call_kwargs = mock_upload.call_args.kwargs
    assert "/c/en.json" in (call_kwargs.get("cookies") or mock_upload.call_args.args)
    assert "Fun fact" in (call_kwargs.get("description", "") or "")


@patch("services.tiktok.upload_tiktok")
def test_publish_tiktok_raises_on_failure(mock_upload):
    from services.tiktok import publish_tiktok

    mock_upload.side_effect = Exception("Cookie expired")

    with pytest.raises(Exception, match="Cookie expired"):
        publish_tiktok(_make_caption(), Path("/v.mp4"), _make_settings(), "en")
