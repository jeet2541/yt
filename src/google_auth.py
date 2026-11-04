import json
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly",
]

def get_google_credentials():
    raw = os.getenv("YOUTUBE_TOKEN_JSON")
    if not raw:
        raise RuntimeError("GitHub Secret YOUTUBE_TOKEN_JSON is missing.")
    try:
        info = json.loads(raw)
        creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)
    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        raise RuntimeError("YOUTUBE_TOKEN_JSON is not valid OAuth token JSON.") from exc

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds.valid:
        raise RuntimeError(
            "Google OAuth token is invalid or expired. Re-authorize and update YOUTUBE_TOKEN_JSON."
        )
    return creds
