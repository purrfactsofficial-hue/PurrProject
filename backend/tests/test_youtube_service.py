from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_caption(title="Cool Title", body="Watch this!", hashtags=None):
    cap = MagicMock()
    cap.title = title
    cap.body = body
    cap.hashtags = hashtags or ["#PurrFacts", "#Shorts", "#Science"]
    return cap


def _make_settings(lang="en"):
    s = MagicMock()
    s.youtube_client_id = "client_id"
    s.youtube_client_secret = "client_secret"
    setattr(s, f"youtube_refresh_token_{lang}", "refresh_tok_123")
    s.made_for_kids = True
    return s


@patch("services.youtube.MediaFileUpload")
@patch("services.youtube.build")
def test_publish_youtube_returns_video_id(mock_build, mock_media):
    from services.youtube import publish_youtube

    mock_yt = MagicMock()
    mock_build.return_value = mock_yt
    mock_yt.videos.return_value.insert.return_value.execute.return_value = {"id": "abc123"}

    result = publish_youtube(_make_caption(), Path("/fake/video.mp4"), _make_settings(), "en")

    assert result == "abc123"


@patch("services.youtube.MediaFileUpload")
@patch("services.youtube.build")
def test_publish_youtube_sets_made_for_kids(mock_build, mock_media):
    from services.youtube import publish_youtube

    mock_yt = MagicMock()
    mock_build.return_value = mock_yt
    insert_mock = mock_yt.videos.return_value.insert
    insert_mock.return_value.execute.return_value = {"id": "vid1"}

    publish_youtube(_make_caption(), Path("/fake/video.mp4"), _make_settings(), "en")

    body = insert_mock.call_args.kwargs["body"]
    assert body["status"]["selfDeclaredMadeForKids"] is True
    assert body["snippet"]["categoryId"] == "27"


@patch("services.youtube.MediaFileUpload")
@patch("services.youtube.build")
def test_publish_youtube_uses_correct_lang_token(mock_build, mock_media):
    from services.youtube import publish_youtube

    mock_yt = MagicMock()
    mock_build.return_value = mock_yt
    mock_yt.videos.return_value.insert.return_value.execute.return_value = {"id": "ukid"}

    s = _make_settings("uk")
    publish_youtube(_make_caption(), Path("/fake/video.mp4"), s, "uk")

    creds_arg = mock_build.call_args.kwargs["credentials"]
    assert creds_arg.refresh_token == "refresh_tok_123"


@patch("services.youtube.MediaFileUpload")
@patch("services.youtube.build")
def test_publish_youtube_raises_on_api_error(mock_build, mock_media):
    from googleapiclient.errors import HttpError

    from services.youtube import publish_youtube

    mock_yt = MagicMock()
    mock_build.return_value = mock_yt
    mock_yt.videos.return_value.insert.return_value.execute.side_effect = HttpError(
        resp=MagicMock(status=403), content=b"quota"
    )

    with pytest.raises(HttpError):
        publish_youtube(_make_caption(), Path("/fake/video.mp4"), _make_settings(), "en")
