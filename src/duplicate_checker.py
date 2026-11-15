
import hashlib
import json
import logging
import os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from config import HISTORY_FILE, TIMEZONE

logger = logging.getLogger(__name__)


def file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_history():
    path = Path(HISTORY_FILE)

    if not path.exists():
        return {"uploaded": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Invalid history format.")

        if not isinstance(data.get("uploaded"), list):
            raise ValueError("Uploaded history must be a list.")

        return data

    except (json.JSONDecodeError, OSError, ValueError):
        logger.exception("Could not read upload history.")
        raise RuntimeError("Upload history is invalid. Stopping safely.")


def save_history(history):
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = path.with_suffix(".json.tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as handle:
            json.dump(history, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_file, path)

    finally:
        if temporary_file.exists():
            temporary_file.unlink(missing_ok=True)


def count_uploads_today():
    history = load_history()
    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    count = 0

    for item in history["uploaded"]:
        if not isinstance(item, dict):
            continue

        timestamp = item.get("uploaded_at")

        if not timestamp:
            continue

        try:
            upload_date = datetime.fromisoformat(timestamp).astimezone(
                ZoneInfo(TIMEZONE)
            ).date()

            if upload_date == today:
                count += 1

        except (ValueError, TypeError):
            logger.warning("Invalid upload timestamp in history.")

    return count


def is_duplicate(drive_file_id, sha256):
    history = load_history()

    for item in history["uploaded"]:
        if not isinstance(item, dict):
            continue

        if (
            item.get("drive_file_id") == drive_file_id
            or item.get("sha256") == sha256
        ):
            return True

    return False


def record_upload(drive_file, sha256, youtube_video_id):
    if not drive_file.get("id"):
        raise ValueError("Drive ID missing.")

    if not sha256 or not youtube_video_id:
        raise ValueError("Upload information missing.")

    history = load_history()

    for item in history["uploaded"]:
        if not isinstance(item, dict):
            continue

        if (
            item.get("drive_file_id") == drive_file["id"]
            or item.get("sha256") == sha256
            or item.get("youtube_video_id") == youtube_video_id
        ):
            logger.warning("Upload already exists in history.")
            return

    history["uploaded"].append({
        "drive_file_id": drive_file["id"],
        "filename": drive_file.get("name", "Unknown"),
        "sha256": sha256,
        "youtube_video_id": youtube_video_id,
        "uploaded_at": datetime.now(
            ZoneInfo(TIMEZONE)
        ).isoformat()
    })

    save_history(history)

    logger.info("Upload history saved: %s", youtube_video_id)
