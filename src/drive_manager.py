import os
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config import DRIVE_FOLDER_ID, VIDEO_EXTENSIONS, DOWNLOAD_DIR
from src.google_auth import get_google_credentials

def get_drive_service():
    return build("drive", "v3", credentials=get_google_credentials(), cache_discovery=False)

def list_videos():
    if not DRIVE_FOLDER_ID:
        raise RuntimeError("GitHub Secret DRIVE_FOLDER_ID is missing.")
    service = get_drive_service()
    found, page_token = [], None
    while True:
        result = service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="nextPageToken,files(id,name,mimeType,size,createdTime)",
            pageSize=100,
            orderBy="createdTime",
            pageToken=page_token,
        ).execute()
        for item in result.get("files", []):
            if Path(item["name"]).suffix.lower() in VIDEO_EXTENSIONS:
                found.append(item)
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    return found

def download_video(file_id, filename):
    service = get_drive_service()
    folder = Path(DOWNLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / Path(filename).name
    request = service.files().get_media(fileId=file_id)
    with destination.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    return str(destination)
