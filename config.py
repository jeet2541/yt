
import os

# YouTube upload settings
DAILY_UPLOAD_LIMIT = int(os.getenv("DAILY_UPLOAD_LIMIT", "1"))
YOUTUBE_PRIVACY = os.getenv("YOUTUBE_PRIVACY", "public")

# Music category = 10
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "10")

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

# Google Drive and YouTube authentication
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")
YOUTUBE_TOKEN_JSON = os.getenv("YOUTUBE_TOKEN_JSON")

# Video settings
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}

# File paths
HISTORY_FILE = "data/upload_history.json"
DOWNLOAD_DIR = "downloads"
