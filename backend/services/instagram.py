import time

import requests

_GRAPH_BASE = "https://graph.facebook.com/v21.0"
_POLL_INTERVAL_SECS = 30
_MAX_POLLS = 10  # 5 minutes maximum


def publish_instagram(caption, public_url: str, settings, lang: str) -> str:
    """Publish a Reel via the Instagram Graph API. Returns the media ID."""
    token = getattr(settings, f"instagram_token_{lang}")
    ig_user_id = getattr(settings, f"instagram_user_id_{lang}")
    caption_text = f"{caption.body} {' '.join(caption.hashtags)}"

    container_resp = requests.post(
        f"{_GRAPH_BASE}/{ig_user_id}/media",
        params={
            "media_type": "REELS",
            "video_url": public_url,
            "caption": caption_text,
            "access_token": token,
        },
    )
    container_resp.raise_for_status()
    container_id = container_resp.json()["id"]

    for _ in range(_MAX_POLLS):
        time.sleep(_POLL_INTERVAL_SECS)
        status_resp = requests.get(
            f"{_GRAPH_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": token},
        )
        status_resp.raise_for_status()
        if status_resp.json().get("status_code") == "FINISHED":
            break
    else:
        raise TimeoutError(f"Instagram container {container_id} did not finish processing")

    publish_resp = requests.post(
        f"{_GRAPH_BASE}/{ig_user_id}/media_publish",
        params={"creation_id": container_id, "access_token": token},
    )
    publish_resp.raise_for_status()
    return publish_resp.json()["id"]
