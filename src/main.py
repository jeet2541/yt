
import logging
import os

from src.ai_metadata import (
    generate_metadata,
    generate_fallback_metadata
)

from src.drive_manager import download_video, list_videos
from src.duplicate_checker import (
    file_sha256,
    is_duplicate,
    record_upload
)
from src.youtube_uploader import upload_video


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def main():
    limit = int(os.getenv("DAILY_UPLOAD_LIMIT", "1"))

    videos = list_videos()
    uploaded_count = 0

    for video in videos:

        if uploaded_count >= limit:
            break

        local_path = None

        try:
            logging.info("Processing video: %s", video["name"])

            local_path = download_video(
                video["id"],
                video["name"]
            )

            digest = file_sha256(local_path)

            if is_duplicate(video["id"], digest):
                logging.info(
                    "Skipping already-uploaded file: %s",
                    video["name"]
                )
                continue

            # Try Gemini first, use local backup if it fails.
            try:
                metadata = generate_metadata(video["name"])

                logging.info(
                    "Gemini AI metadata generated successfully."
                )

            except Exception:
                logging.exception(
                    "Gemini failed. Switching to local fallback metadata."
                )

                metadata = generate_fallback_metadata(
                    video["name"]
                )

            logging.info("Selected title: %s", metadata["title"])

            youtube_id = upload_video(
                local_path,
                metadata
            )

            record_upload(
                video,
                digest,
                youtube_id
            )

            uploaded_count += 1

            logging.info(
                "Uploaded successfully: %s | YouTube ID: %s",
                video["name"],
                youtube_id
            )

        except Exception:
            logging.exception(
                "Video processing failed: %s",
                video["name"]
            )

        finally:
            if local_path and os.path.exists(local_path):
                os.remove(local_path)

    logging.info(
        "Run complete. New uploads: %s",
        uploaded_count
    )


if __name__ == "__main__":
    main()
