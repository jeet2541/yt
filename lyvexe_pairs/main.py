
import os
import json
import tempfile
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload


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
    requested = Path(requested_name).stem.lower()

    files = list_folder_files(drive, folder_id)

    matches = []

    for item in files:
        filename = item["name"]
        extension = Path(filename).suffix.lower()
        stem = Path(filename).stem.lower()

        if extension not in allowed_extensions:
            continue

        if stem == requested:
            matches.append(item)

    if not matches:
        raise FileNotFoundError(
            f"File not found in Drive: {requested_name}"
        )

    if len(matches) > 1:
        names = [item["name"] for item in matches]

        raise RuntimeError(
            f"Multiple files match '{requested_name}': {names}. "
            "Keep only one matching file in the folder."
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

    matches = [
        item for item in files
        if item["name"] == STATE_FILE_NAME
    ]

    if len(matches) > 1:
        raise RuntimeError("Multiple LYVEXE state files found.")

    if not matches:
        return None, {
            "next_pair": 0,
            "uploaded": [],
            "status": "ready",
            "next_upload_at": None
        }

    file_id = matches[0]["id"]

    request = drive.files().get_media(fileId=file_id)
    content = request.execute()

    if isinstance(content, bytes):
        content = content.decode("utf-8")

    return file_id, json.loads(content)


def save_state(drive, file_id, state):
    temporary_path = (
        Path(tempfile.gettempdir()) / STATE_FILE_NAME
    )

    temporary_path.write_text(
        json.dumps(state, indent=2),
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
            "ffprobe",
            "-v", "error",
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
        raise RuntimeError("Invalid media duration.")

    return duration


def check_audio_stream(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
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
        raise RuntimeError("FFmpeg and FFprobe must be installed.")

    if not check_audio_stream(song_path):
        raise RuntimeError("Selected song has no audio stream.")

    song_duration = probe_duration(song_path)

    print(f"Song duration: {song_duration:.2f} seconds")
    print("Video will loop until the song finishes.")
    print("Original video audio will not be included.")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",

        # Loop video indefinitely
        "-stream_loop", "-1",
        "-i", str(video_path),

        # Song plays once, for its full duration
        "-i", str(song_path),

        # Only original video stream and selected song audio
        "-map", "0:v:0",
        "-map", "1:a:0",

        # Horizontal 1920x1080 output, preserve aspect ratio
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1",

        # CPU encoding for GitHub Actions
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",

        # Audio settings
        "-c:a", "aac",
        "-b:a", "320k",
        "-ar", "48000",
        "-ac", "2",

        # Stop when the song ends
        "-t", str(song_duration),

        "-movflags", "+faststart",
        str(output_path)
    ]

    print("Starting FFmpeg render...")

    subprocess.run(command, check=True)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Output video was not created.")

    print("Video rendering completed.")


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


def upload_to_youtube(youtube, output_path, pair_number):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": f"LYVEXE | Video Song #{pair_number}",
                "description": "LYVEXE - Music and Visuals.",
                "categoryId": "10"
            },
            "status": {
                "privacyStatus": "public",
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
    print("=" * 55)
    print("          LYVEXE VIDEO AUTOMATION")
    print("=" * 55)

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg or FFprobe is missing.")

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        config = json.load(file)

    pairs = config.get("pairs", [])

    if len(pairs) != 20:
        raise ValueError("config.json must contain exactly 20 pairs.")

    drive, youtube = authenticate()

    state_id, state = get_state(drive)

    if state.get("status") == "uploading":
        raise RuntimeError(
            "Previous upload has an uncertain result. "
            "Check YouTube Studio before retrying."
        )

    if state.get("next_pair", 0) >= 20:
        print("All 20 pairs have been processed.")
        return

    if state.get("next_upload_at"):
        next_time = datetime.fromisoformat(
            state["next_upload_at"]
        )

        if now_utc() < next_time:
            print("Not an upload day yet. Skipping.")
            return

    index = state["next_pair"]
    pair = pairs[index]

    video_name = pair.get("video", "").strip()
    song_name = pair.get("song", "").strip()

    if not video_name or not song_name:
        raise ValueError(
            f"Pair {index + 1} is incomplete. "
            "Fill its video and song names in config.json."
        )

    pair_number = index + 1

    print(f"Selected pair: {pair_number}/20")
    print(f"Video: {video_name}")
    print(f"Song: {song_name}")

    video = find_drive_file(
        drive,
        VIDEO_FOLDER_ID,
        video_name,
        VIDEO_EXTENSIONS
    )

    song = find_drive_file(
        drive,
        SONG_FOLDER_ID,
        song_name,
        AUDIO_EXTENSIONS
    )

    with tempfile.TemporaryDirectory() as temporary:
        temporary = Path(temporary)

        video_path = temporary / video["name"]
        song_path = temporary / song["name"]

        output_path = temporary / f"LYVEXE_{pair_number:02d}.mp4"

        download_drive_file(drive, video["id"], video_path)
        download_drive_file(drive, song["id"], song_path)

        render_video(video_path, song_path, output_path)

        # Record upload intent before contacting YouTube.
        # Never automatically retry an uncertain upload.
        state["status"] = "uploading"
        state["uploading_pair"] = pair_number
        state["upload_started_at"] = now_utc().isoformat()

        state_id = save_state(drive, state_id, state)

        generated = upload_generated_to_drive(
            drive,
            output_path
        )

        youtube_id = upload_to_youtube(
            youtube,
            output_path,
            pair_number
        )

        uploaded_at = now_utc()

        state["uploaded"].append({
            "pair": pair_number,
            "video_file_id": video["id"],
            "song_file_id": song["id"],
            "generated_file_id": generated["id"],
            "youtube_video_id": youtube_id,
            "uploaded_at": uploaded_at.isoformat(),
            "delete_after": (
                uploaded_at + timedelta(hours=1)
            ).isoformat()
        })

        state["next_pair"] = index + 1
        state["next_upload_at"] = (
            uploaded_at + timedelta(days=2)
        ).isoformat()

        state["status"] = "ready"
        state.pop("uploading_pair", None)
        state.pop("upload_started_at", None)

        state_id = save_state(drive, state_id, state)

        print("=" * 55)
        print("LYVEXE UPLOAD SUCCESSFUL")
        print(f"YouTube video ID: {youtube_id}")
        print(f"Generated Drive file: {generated['name']}")
        print("Next upload interval: 2 days")
        print("=" * 55)


if __name__ == "__main__":
    main()
