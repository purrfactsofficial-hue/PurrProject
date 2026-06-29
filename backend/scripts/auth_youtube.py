"""One-time helper — run to mint a YouTube refresh token and print it for .env."""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    client_id = input("YouTube Client ID: ").strip()
    client_secret = input("YouTube Client Secret: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n--- Paste this into .env ---")
    lang = input("Which language channel? (en/uk/zh/fr): ").strip().lower()
    print(f"YOUTUBE_CLIENT_ID={client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN_{lang.upper()}={creds.refresh_token}")
    print("----------------------------")


if __name__ == "__main__":
    main()
