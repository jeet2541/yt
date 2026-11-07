
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


TOKEN_JSON = os.environ["LYVEXE_PAIRS_TOKEN_JSON"]
GENERATED_FOLDER_ID = os.environ["LYVEXE_GENERATED_FOLDER_ID"]
STATE_FILE_NAME = ".lyvexe_pairs_state.json"


def authenticate():
    credentials = Credentials.from_authorized_user_info(
        json.loads(TOKEN_JSON),
        [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/youtube.upload"
        ]
    )
    return build("drive", "v3", credentials=credentials)


def find_state_file(drive):
    result = drive.files().list(
        q=(
            f"'{GENERATED_FOLDER_ID}' in parents and "
            f"name='{STATE_FILE_NAME}' and trashed=false"
        ),
        fields="files(id,name)",
        pageSize=10
    ).execute()

    files = result.get("files", [])

    if len(files) > 1:
        raise RuntimeError("Multiple state files found.")

    return files[0] if files else None


def save_state(drive, state_file_id, state):
    temp_path = Path(tempfile.gettempdir()) / STATE_FILE_NAME
    temp_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    media = MediaFileUpload(
        str(temp_path),
        mimetype="application/json",
        resumable=False
    )

    drive.files().update(
        fileId=state_file_id,
        media_body=media
    ).execute()


def main():
    drive = authenticate()
    state_file = find_state_file(drive)

    if not state_file:
        print("No LYVEXE state file found. Nothing to clean.")
        return

    request = drive.files().get_media(fileId=state_file["id"])
    content = request.execute()

    if isinstance(content, bytes):
        content = content.decode("utf-8")

    state = json.loads(content)
    now = datetime.now(timezone.utc)

    deleted_count = 0

    for item in state.get("uploaded", []):
        file_id = item.get("generated_file_id")
        delete_after = item.get("delete_after")

        if not file_id or not delete_after:
            continue

        due_time = datetime.fromisoformat(
            delete_after.replace("Z", "+00:00")
        )

        if item.get("deleted"):
            continue

        if now < due_time:
            continue

        try:
            drive.files().delete(fileId=file_id).execute()
            item["deleted"] = True
            item["deleted_at"] = now.isoformat()
            deleted_count += 1
            print(f"Deleted generated file: {file_id}")

        except Exception as error:
            print(f"Could not delete {file_id}: {error}")

    save_state(drive, state_file["id"], state)

    print(f"Cleanup complete. Deleted files: {deleted_count}")


if __name__ == "__main__":
    main()
