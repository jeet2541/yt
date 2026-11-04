
import logging
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from config import DRIVE_FOLDER_ID, VIDEO_EXTENSIONS, DOWNLOAD_DIR
from src.google_auth import get_google_credentials


def get_drive_service():
    return build(
        "drive",
        "v3",
        credentials=get_google_credentials(),
        cache_discovery=False
    )


def list_videos():
    if not DRIVE_FOLDER_ID:
        raise RuntimeError("GitHub Secret DRIVE_FOLDER_ID is missing.")

    service = get_drive_service()
    found = []
    page_token = None

    while True:
        result = service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
            fields="nextPageToken,files(id,name,mimeType,size,createdTime)",
            pageSize=100,
            orderBy="createdTime",
            pageToken=page_token,
        ).execute()

        for item in result.get("files", []):
            filename = item.get("name", "")
            mime_type = item.get("mimeType", "")

            if (
                Path(filename).suffix.lower() in VIDEO_EXTENSIONS
                and mime_type.startswith("video/")
            ):
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

    try:
        with destination.open("wb") as handle:
            downloader = MediaIoBaseDownload(
                handle,
                request,
                chunksize=8 * 1024 * 1024
            )

            done = False

            while not done:
                status, done = downloader.next_chunk()

                if status:
                    logging.info(
                        "Download progress: %d%%",
                        int(status.progress() * 100)
                    )

        actual_size = destination.stat().st_size

        drive_file = service.files().get(
            fileId=file_id,
            fields="size"
        ).execute()

        expected_size = int(drive_file.get("size", 0))

        if expected_size and actual_size != expected_size:
            raise RuntimeError(
                f"Download size mismatch. "
                f"Expected: {expected_size}, Got: {actual_size}"
            )

        if actual_size == 0:
            raise RuntimeError("Downloaded video is empty.")

        logging.info(
            "Original video downloaded and verified: %s (%.2f MB)",
            filename,
            actual_size / (1024 * 1024)
        )

        return str(destination)

    except Exception:
        destination.unlink(missing_ok=True)
        raise
