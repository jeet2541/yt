import os

DAILY_UPLOAD_LIMIT = int(os.getenv("DAILY_UPLOAD_LIMIT", "1"))
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "private")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
YOUTUBE_TOKEN_JSON = os.getenv("YOUTUBE_TOKEN_JSON")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
HISTORY_FILE = "data/upload_history.json"
DOWNLOAD_DIR = "downloads"
