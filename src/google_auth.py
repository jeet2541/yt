
import json
import os
import logging

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.readonly",
]


def get_google_credentials():
    raw = os.getenv("YOUTUBE_TOKEN_JSON")

    if not raw:
        raise RuntimeError(
            "GitHub Secret YOUTUBE_TOKEN_JSON is missing."
        )

    try:
        info = json.loads(raw)

        creds = Credentials.from_authorized_user_info(
            info,
            scopes=SCOPES
        )

    except (json.JSONDecodeError, ValueError, KeyError) as exc:
        raise RuntimeError(
            "YOUTUBE_TOKEN_JSON is not valid OAuth token JSON."
        ) from exc

    if creds.expired:
        if not creds.refresh_token:
            raise RuntimeError(
                "OAuth access token expired and refresh token is missing. "
                "Generate a fresh OAuth token."
            )

        logger.info("Refreshing Google OAuth access token...")

        try:
            creds.refresh(Request())

        except RefreshError as exc:
            logger.exception("Google OAuth refresh failed.")

            raise RuntimeError(
                "Google OAuth refresh failed. The refresh token may "
                "have expired or been revoked. Re-authorize Google "
                "and update YOUTUBE_TOKEN_JSON in GitHub Secrets."
            ) from exc

    if not creds.valid:
        raise RuntimeError(
            "Google OAuth credentials are invalid. "
            "Fresh authorization is required."
        )

    logger.info("Google OAuth authentication successful.")

    return creds
