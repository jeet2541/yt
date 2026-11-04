import os

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import YOUTUBE_PRIVACY, YOUTUBE_CATEGORY_ID
from src.google_auth import get_google_credentials

def upload_video(file_path, metadata):
    service = build("youtube", "v3", credentials=get_google_credentials(), cache_discovery=False)
    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": {
            "privacyStatus": YOUTUBE_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(file_path, mimetype="video/*", chunksize=8 * 1024 * 1024, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]
