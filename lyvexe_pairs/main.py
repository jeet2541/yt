import os
import json
import tempfile
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


# ============================================================
# LYVEXE PAIRS AUTOMATION
# Independent from the existing Shorts automation.
# Reads pair-specific title, description and tags from config.json.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

TOKEN_JSON = os.environ["LYVEXE_PAIRS_TOKEN_JSON"]
VIDEO_FOLDER_ID = os.environ["LYVEXE_VIDEOS_FOLDER_ID"]
SONG_FOLDER_ID = os.environ["LYVEXE_SONGS_FOLDER_ID"]
GENERATED_FOLDER_ID = os.environ["LYVEXE_GENERATED_FOLDER_ID"]

STATE_FILE_NAME = ".lyvexe_pairs_state.json"

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v",
    ".mpeg", ".mpg", ".wmv", ".flv", ".3gp"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac",
    ".wma", ".opus"
}

YOUTUBE_CATEGORY_ID = "10"  # Music
YOUTUBE_PRIVACY = "public"
UPLOAD_INTERVAL_DAYS = 2

# This is a fallback description only. Prefer putting a tailored
# description in each config.json pair.
CHANNEL_FOOTER = """✦ Follow Lyvexe:
• YouTube: https://www.youtube.com/@lyvexe

All the videos, songs, images, and graphics used in the video belong to their respective owners. This channel does not claim ownership of third-party content.

Copyright Disclaimer under Section 107 of the Copyright Act of 1976: Allowance is made for fair use for purposes such as criticism, comment, news reporting, teaching, scholarship, education and research. Fair use is a use permitted by copyright statute that might otherwise be infringing.

Disclaimer: All visuals and audio compositions are curated/produced to offer immersive listening experiences. For inquiries or copyright concerns, please reach out directly via the channel About page or listed contact email."""


def now_utc():
    return datetime.now(timezone.utc)


def authenticate():
    token_data = json.loads(TOKEN_JSON)
    credentials = Credentials.from_authorized_user_info(
        token_data,
        [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/youtube.upload"
        ]
    )
    drive = build("drive", "v3", credentials=credentials)
    youtube = build("youtube", "v3", credentials=credentials)
    return drive, youtube


def list_folder_files(drive, folder_id):
    files = []
    page_token = None

    while True:
        result = drive.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken,files(id,name,mimeType,size)",
            pageSize=1000,
            pageToken=page_token
        ).execute()

        files.extend(result.get("files", []))
        page_token = result.get("nextPageToken")

        if not page_token:
            break

    return files


def find_drive_file(drive, folder_id, requested_name, allowed_extensions):
    requested = Path(requested_name).stem.strip().lower()
    files = list_folder_files(drive, folder_id)
    matches = []

    for item in files:
        filename = item["name"]
        extension = Path(filename).suffix.lower()
        stem = Path(filename).stem.strip().lower()

        if extension in allowed_extensions and stem == requested:
            matches.append(item)

    if not matches:
        raise FileNotFoundError(
            f"File not found in Drive folder: {requested_name}"
        )

    if len(matches) > 1:
        names = [item["name"] for item in matches]
        raise RuntimeError(
            f"More than one file matches '{requested_name}': {names}. "
            "Keep exactly one matching file in the folder."
        )

    return matches[0]


def download_drive_file(drive, file_id, destination):
    request = drive.files().get_media(fileId=file_id)

    with open(destination, "wb") as output:
        downloader = MediaIoBaseDownload(output, request)
        done = False

        while not done:
            _, done = downloader.next_chunk()


def get_state(drive):
    files = list_folder_files(drive, GENERATED_FOLDER_ID)
    matches = [item for item in files if item["name"] == STATE_FILE_NAME]

    if len(matches) > 1:
        raise RuntimeError("Multiple LYVEXE state files found in Generated folder.")

    if not matches:
        return None, {
            "next_pair": 0,
            "uploaded": [],
            "status": "ready",
            "next_upload_at": None
        }

    file_id = matches[0]["id"]
    content = drive.files().get_media(fileId=file_id).execute()

    if isinstance(content, bytes):
        content = content.decode("utf-8")

    return file_id, json.loads(content)


def save_state(drive, file_id, state):
    temporary_path = Path(tempfile.gettempdir()) / STATE_FILE_NAME
    temporary_path.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    media = MediaFileUpload(
        str(temporary_path),
        mimetype="application/json",
        resumable=False
    )

    if file_id:
        drive.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        return file_id

    result = drive.files().create(
        body={
            "name": STATE_FILE_NAME,
            "parents": [GENERATED_FOLDER_ID]
        },
        media_body=media,
        fields="id"
    ).execute()

    return result["id"]


def probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError(f"Invalid media duration: {path.name}")

    return duration


def check_audio_stream(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(path)
        ],
        capture_output=True,
        text=True
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def render_video(video_path, song_path, output_path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe must be installed on the runner.")

    if not check_audio_stream(song_path):
        raise RuntimeError("Selected song has no audio stream.")

    song_duration = probe_duration(song_path)

    print(f"Song duration: {song_duration:.2f} seconds")
    print("Video will loop until the song finishes.")
    print("Original video audio will be muted.")
    print("Output format: horizontal 1920x1080.")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-stream_loop", "-1",
        "-i", str(video_path),
        "-i", str(song_path),

        # Only video from input 0 and audio from input 1.
        "-map", "0:v:0",
        "-map", "1:a:0",

        # Keep the full horizontal frame without stretching.
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",

        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        "-ac", "2",

        # End exactly when the selected song ends.
        "-t", f"{song_duration:.3f}",
        "-movflags", "+faststart",
        str(output_path)
    ]

    print("Starting FFmpeg render...")
    subprocess.run(command, check=True)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg did not create a valid output video.")

    print(f"Render complete: {output_path.stat().st_size:,} bytes")


def upload_generated_to_drive(drive, output_path):
    media = MediaFileUpload(
        str(output_path),
        mimetype="video/mp4",
        resumable=True
    )

    result = drive.files().create(
        body={
            "name": output_path.name,
            "parents": [GENERATED_FOLDER_ID]
        },
        media_body=media,
        fields="id,name"
    ).execute()

    return result


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def prepare_metadata(pair, pair_number):
    title = clean_text(pair.get("title"))

    if not title:
        raise ValueError(
            f"Pair {pair_number}: add a unique 'title' in config.json."
        )

    if len(title) > 100:
        raise ValueError(
            f"Pair {pair_number}: YouTube title exceeds 100 characters."
        )

    description = str(pair.get("description") or "").strip()

    if not description:
        description = (
            "An atmospheric music and visual experience from LYVEXE.\n\n"
            "🎧 Put on your headphones and enjoy."
        )

    music_credit = clean_text(pair.get("music_credit"))
    if music_credit and music_credit.lower() not in description.lower():
        description += f"\n\n🎧 Music: {music_credit}"

    # Append the channel footer once, unless the pair description already
    # includes the channel link.
    if "youtube.com/@lyvexe" not in description.lower():
        description += "\n\n" + CHANNEL_FOOTER

    raw_tags = pair.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = [tag.strip() for tag in raw_tags.split(",")]

    tags = []
    seen = set()

    for tag in raw_tags:
        tag = clean_text(tag).lstrip("#")
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)

    # YouTube tags have a total character limit; trim safely.
    final_tags = []
    total_chars = 0

    for tag in tags:
        added = len(tag) + (1 if final_tags else 0)
        if total_chars + added > 450:
            break
        final_tags.append(tag)
        total_chars += added

    # Do not automatically inject unrelated "viral/fyp/trending" tags.
    return {
        "title": title,
        "description": description,
        "tags": final_tags
    }


def upload_to_youtube(youtube, output_path, metadata):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata["tags"],
                "categoryId": YOUTUBE_CATEGORY_ID
            },
            "status": {
                "privacyStatus": YOUTUBE_PRIVACY,
                "selfDeclaredMadeForKids": False
            }
        },
        media_body=MediaFileUpload(
            str(output_path),
            mimetype="video/mp4",
            resumable=True
        )
    )

    response = None
    while response is None:
        _, response = request.next_chunk()

    return response["id"]


def main():
    print("=" * 60)
    print("             LYVEXE VIDEO PAIRS AUTOMATION")
    print("=" * 60)

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg or FFprobe is missing.")

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    pairs = config.get("pairs", [])
    if len(pairs) != 20:
        raise ValueError("config.json must contain exactly 20 pairs.")

    drive, youtube = authenticate()
    state_id, state = get_state(drive)

    # A previous run may have reached YouTube but failed before saving
    # its returned video ID. Do not retry automatically: check Studio first.
    if state.get("status") == "uploading":
        raise RuntimeError(
            "Previous upload has an uncertain result. Check YouTube Studio "
            "for the video before changing the state or retrying."
        )

    index = int(state.get("next_pair", 0))
    if index >= len(pairs):
        print("All 20 pairs have been processed.")
        return

    next_upload_at = state.get("next_upload_at")
    if next_upload_at:
        next_time = datetime.fromisoformat(next_upload_at)
        if now_utc() < next_time:
            print(f"Not an upload day yet. Next eligible time: {next_time}")
            return

    pair = pairs[index]
    pair_number = index + 1

    video_name = clean_text(pair.get("video"))
    song_name = clean_text(pair.get("song"))

    if not video_name or not song_name:
        raise ValueError(
            f"Pair {pair_number} is missing its video or song filename."
        )

    metadata = prepare_metadata(pair, pair_number)

    print(f"Selected pair: {pair_number}/20")
    print(f"Video: {video_name}")
    print(f"Song: {song_name}")
    print(f"Title: {metadata['title']}")
    print(f"Tags: {', '.join(metadata['tags'])}")

    video = find_drive_file(
        drive, VIDEO_FOLDER_ID, video_name, VIDEO_EXTENSIONS
    )
    song = find_drive_file(
        drive, SONG_FOLDER_ID, song_name, AUDIO_EXTENSIONS
    )

    # Prevent accidentally selecting a source already used by an earlier pair.
    used_video_ids = {
        item.get("video_file_id") for item in state.get("uploaded", [])
    }
    used_song_ids = {
        item.get("song_file_id") for item in state.get("uploaded", [])
    }

    if video["id"] in used_video_ids or song["id"] in used_song_ids:
        raise RuntimeError(
            "This source video or song has already been used by a completed "
            "pair. Choose a different source file in config.json."
        )

    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)
        video_path = temporary / video["name"]
        song_path = temporary / song["name"]
        output_path = temporary / f"LYVEXE_{pair_number:02d}.mp4"

        download_drive_file(drive, video["id"], video_path)
        download_drive_file(drive, song["id"], song_path)

        render_video(video_path, song_path, output_path)

        # Save intent before calling YouTube. If the runner stops during
        # upload, the next run blocks for a manual Studio check.
        state["status"] = "uploading"
        state["uploading_pair"] = pair_number
        state["upload_started_at"] = now_utc().isoformat()
        state_id = save_state(drive, state_id, state)

        # Keep a Drive copy so cleanup can remove it one hour after upload.
        generated = upload_generated_to_drive(drive, output_path)

        youtube_id = upload_to_youtube(
            youtube,
            output_path,
            metadata
        )

        uploaded_at = now_utc()

        state.setdefault("uploaded", []).append({
            "pair": pair_number,
            "video_file_id": video["id"],
            "song_file_id": song["id"],
            "generated_file_id": generated["id"],
            "youtube_video_id": youtube_id,
            "title": metadata["title"],
            "uploaded_at": uploaded_at.isoformat(),
            "delete_after": (
                uploaded_at + timedelta(hours=1)
            ).isoformat()
        })

        state["next_pair"] = index + 1
        state["next_upload_at"] = (
            uploaded_at + timedelta(days=UPLOAD_INTERVAL_DAYS)
        ).isoformat()
        state["status"] = "ready"
        state.pop("uploading_pair", None)
        state.pop("upload_started_at", None)

        save_state(drive, state_id, state)

        print("=" * 60)
        print("LYVEXE UPLOAD SUCCESSFUL")
        print(f"YouTube video ID: {youtube_id}")
        print(f"Title: {metadata['title']}")
        print(f"Generated Drive file: {generated['name']}")
        print(f"Next eligible upload: {state['next_upload_at']}")
        print("Generated Drive copy is scheduled for cleanup after 1 hour.")
        print("=" * 60)


if __name__ == "__main__":
    main()
