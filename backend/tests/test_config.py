from config import Settings


def test_settings_defaults_for_credentials():
    s = Settings()
    assert s.youtube_client_id == ""
    assert s.youtube_refresh_token_en == ""
    assert s.youtube_refresh_token_uk == ""
    assert s.youtube_refresh_token_zh == ""
    assert s.youtube_refresh_token_fr == ""
    assert s.tiktok_cookies_en == ""
    assert s.tiktok_cookie_warn_days == 21
    assert s.instagram_token_en == ""
    assert s.instagram_user_id_en == ""
    assert s.ig_public_url_mode == "tunnel"
    assert s.made_for_kids is True
