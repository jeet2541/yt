
import hashlib
import json
import logging
import os
from pathlib import Path

from config import HISTORY_FILE

logger = logging.getLogger(__name__)


# =========================================================
# FILE HASH
# =========================================================

def file_sha256(path):
    digest = hashlib.sha256()

    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


# =========================================================
# HISTORY
# =========================================================

def load_history():
    path = Path(HISTORY_FILE)

    if not path.exists():
        return {"uploaded": []}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(data, dict):
            raise ValueError("Invalid upload history format.")

        if not isinstance(data.get("uploaded"), list):
            raise ValueError("Upload history must contain an uploaded list.")

        return data

    except (json.JSONDecodeError, OSError, ValueError):
        logger.exception(
            "Upload history could not be read. "
            "Preserving the existing file and stopping is safer."
        )
        raise RuntimeError(
            "Upload history is invalid or unreadable. "
            "Fix the history file before uploading."
        )


def save_history(history):
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = path.with_suffix(path.suffix + ".tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as handle:
            json.dump(
                history,
                handle,
                indent=2,
                ensure_ascii=False
            )
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_file, path)

    finally:
        if temporary_file.exists():
            temporary_file.unlink(missing_ok=True)


# =========================================================
# DUPLICATE CHECK
# =========================================================

def is_duplicate(drive_file_id, sha256):
    history = load_history()

    for item in history["uploaded"]:
        if not isinstance(item, dict):
            continue

        if (
            item.get("drive_file_id") == drive_file_id
            or item.get("sha256") == sha256
        ):
            logger.info(
                "Duplicate found | Drive ID: %s | SHA256: %s",
                drive_file_id,
                sha256
            )
            return True

    return False


# =========================================================
# RECORD SUCCESSFUL UPLOAD
# =========================================================

def record_upload(drive_file, sha256, youtube_video_id):
    if not drive_file.get("id"):
        raise ValueError("Drive file ID is missing.")

    if not sha256:
        raise ValueError("SHA256 hash is missing.")

    if not youtube_video_id:
        raise ValueError("YouTube video ID is missing.")

    history = load_history()

    # Avoid adding the same upload twice.
    for item in history["uploaded"]:
        if not isinstance(item, dict):
            continue

        if (
            item.get("drive_file_id") == drive_file["id"]
            or item.get("sha256") == sha256
            or item.get("youtube_video_id") == youtube_video_id
        ):
            logger.warning(
                "Upload already exists in history. "
                "Drive ID: %s",
                drive_file["id"]
            )
            return

    history["uploaded"].append({
        "drive_file_id": drive_file["id"],
        "filename": drive_file.get("name", "Unknown"),
        "sha256": sha256,
        "youtube_video_id": youtube_video_id,
    })

    save_history(history)

    logger.info(
        "Upload history saved successfully | YouTube ID: %s",
        youtube_video_id
    )
