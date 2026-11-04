import hashlib
import json
from pathlib import Path

from config import HISTORY_FILE

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
        if not isinstance(data.get("uploaded"), list):
            return {"uploaded": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"uploaded": []}

def is_duplicate(drive_file_id, sha256):
    for item in load_history()["uploaded"]:
        if item.get("drive_file_id") == drive_file_id or item.get("sha256") == sha256:
            return True
    return False

def record_upload(drive_file, sha256, youtube_video_id):
    history = load_history()
    history["uploaded"].append({
        "drive_file_id": drive_file["id"],
        "filename": drive_file["name"],
        "sha256": sha256,
        "youtube_video_id": youtube_video_id,
    })
    path = Path(HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
