from unittest.mock import MagicMock, patch

import pytest


def _make_caption(body="Amazing!", hashtags=None):
    cap = MagicMock()
    cap.body = body
    cap.hashtags = hashtags or ["#P1", "#P2", "#P3", "#P4", "#P5"]
    return cap


def _make_settings(lang="en"):
    s = MagicMock()
    setattr(s, f"instagram_token_{lang}", "tok_abc")
    setattr(s, f"instagram_user_id_{lang}", "ig_user_123")
    return s


@patch("services.instagram.time.sleep")
@patch("services.instagram.requests.get")
@patch("services.instagram.requests.post")
def test_publish_instagram_happy_path(mock_post, mock_get, mock_sleep):
    from services.instagram import publish_instagram

    # Step 1: create container
    mock_post.side_effect = [
        MagicMock(json=lambda: {"id": "container_abc"}, raise_for_status=lambda: None),
        MagicMock(json=lambda: {"id": "media_xyz"}, raise_for_status=lambda: None),
    ]
    # Step 2: poll → FINISHED on first poll
    mock_get.return_value = MagicMock(
        json=lambda: {"status_code": "FINISHED"}, raise_for_status=lambda: None
    )

    result = publish_instagram(
        _make_caption(), "https://abc.trycloudflare.com/media/5.mp4", _make_settings(), "en"
    )

    assert result == "media_xyz"
    assert mock_post.call_count == 2


@patch("services.instagram.time.sleep")
@patch("services.instagram.requests.get")
@patch("services.instagram.requests.post")
def test_publish_instagram_polls_until_finished(mock_post, mock_get, mock_sleep):
    from services.instagram import publish_instagram

    mock_post.side_effect = [
        MagicMock(json=lambda: {"id": "cont_1"}, raise_for_status=lambda: None),
        MagicMock(json=lambda: {"id": "media_1"}, raise_for_status=lambda: None),
    ]
    # First two polls return IN_PROGRESS; third returns FINISHED
    mock_get.side_effect = [
        MagicMock(json=lambda: {"status_code": "IN_PROGRESS"}, raise_for_status=lambda: None),
        MagicMock(json=lambda: {"status_code": "IN_PROGRESS"}, raise_for_status=lambda: None),
        MagicMock(json=lambda: {"status_code": "FINISHED"}, raise_for_status=lambda: None),
    ]

    result = publish_instagram(_make_caption(), "https://x.com/media/5.mp4", _make_settings(), "en")

    assert result == "media_1"
    assert mock_get.call_count == 3


@patch("services.instagram.time.sleep")
@patch("services.instagram.requests.get")
@patch("services.instagram.requests.post")
def test_publish_instagram_raises_on_timeout(mock_post, mock_get, mock_sleep):
    from services.instagram import _MAX_POLLS, publish_instagram

    mock_post.side_effect = [
        MagicMock(json=lambda: {"id": "cont_t"}, raise_for_status=lambda: None),
        MagicMock(json=lambda: {"id": "media_t"}, raise_for_status=lambda: None),
    ]
    mock_get.return_value = MagicMock(
        json=lambda: {"status_code": "IN_PROGRESS"}, raise_for_status=lambda: None
    )

    with pytest.raises(TimeoutError):
        publish_instagram(_make_caption(), "https://x.com/media/5.mp4", _make_settings(), "en")

    assert mock_get.call_count == _MAX_POLLS
