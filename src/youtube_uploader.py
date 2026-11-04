
import os
import logging

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import YOUTUBE_PRIVACY, YOUTUBE_CATEGORY_ID
from src.google_auth import get_google_credentials


def upload_video(file_path, metadata):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Video not found: {file_path}")

    required_fields = ("title", "description", "tags")
    for field in required_fields:
        if field not in metadata:
            raise ValueError(f"Missing metadata field: {field}")

    file_size = os.path.getsize(file_path)

    if file_size == 0:
        raise ValueError(f"Video file is empty: {file_path}")

    logging.info(
        "Starting original-quality upload | File size: %.2f MB",
        file_size / (1024 * 1024)
    )

    service = build(
        "youtube",
        "v3",
        credentials=get_google_credentials(),
        cache_discovery=False
    )

    body = {
        "snippet": {
            "title": str(metadata["title"])[:100],
            "description": str(metadata["description"]),
            "tags": metadata["tags"],
            "categoryId": str(YOUTUBE_CATEGORY_ID),
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    # Upload the original video directly.
    # No compression, resizing, FPS conversion, or re-encoding.
    media = MediaFileUpload(
        file_path,
        mimetype="video/*",
        chunksize=8 * 1024 * 1024,
        resumable=True
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    last_progress = -1

    while response is None:
        status, response = request.next_chunk()

        if status:
            progress = int(status.progress() * 100)

            if progress != last_progress:
                logging.info("Upload progress: %d%%", progress)
                last_progress = progress

    video_id = response.get("id")

    if not video_id:
        raise RuntimeError("Upload response did not contain a YouTube video ID.")

    logging.info(
        "Upload completed successfully | YouTube ID: %s",
        video_id
    )

    return video_id
