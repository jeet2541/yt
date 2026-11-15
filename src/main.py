
import os
import logging

from src.ai_metadata import generate_metadata, commit_title
from src.drive_manager import download_video, list_videos

from src.duplicate_checker import (
    file_sha256,
    is_duplicate,
    record_upload,
    count_uploads_today,
)

from src.youtube_uploader import upload_video


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# Maximum one upload per workflow run
RUN_UPLOAD_LIMIT = int(os.getenv("DAILY_UPLOAD_LIMIT", "1"))

# Maximum three uploads across all runs in one IST day
DAILY_TOTAL_LIMIT = int(os.getenv("DAILY_TOTAL_LIMIT", "3"))


def main():

    logger.info("=" * 60)
    logger.info("YOUTUBE MUSIC AUTOMATION STARTED")
    logger.info("=" * 60)

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    if RUN_UPLOAD_LIMIT <= 0 or DAILY_TOTAL_LIMIT <= 0:
        logger.error("Invalid upload limits.")
        return

    # Check persistent daily history
    try:
        daily_count = count_uploads_today()
    except Exception:
        logger.exception("Could not check daily upload history.")
        return

    logger.info("Already uploaded today: %s", daily_count)
    logger.info("Daily maximum: %s", DAILY_TOTAL_LIMIT)
    logger.info("Per-run maximum: %s", RUN_UPLOAD_LIMIT)

    if daily_count >= DAILY_TOTAL_LIMIT:
        logger.info("Daily limit reached. Skipping this run.")
        return

    try:
        videos = list_videos()
    except Exception:
        logger.exception("Could not retrieve Google Drive videos.")
        return

    if not videos:
        logger.info("No videos found.")
        return

    logger.info("Videos found: %s", len(videos))

    for video in videos:

        # Per-run limit
        if uploaded_count >= RUN_UPLOAD_LIMIT:
            logger.info("Per-run upload limit reached.")
            break

        # Daily limit (recheck persistent history)
        try:
            daily_count = count_uploads_today()
        except Exception:
            logger.exception("Could not verify daily upload count.")
            break

        if daily_count >= DAILY_TOTAL_LIMIT:
            logger.info("Daily upload limit reached.")
            break

        local_path = None
        upload_succeeded = False
        youtube_id = None

        video_name = video.get("name", "Unknown")
        video_id = video.get("id")

        try:

            if not video_id:
                skipped_count += 1
                continue

            logger.info("-" * 60)
            logger.info("PROCESSING: %s", video_name)

            # Download
            local_path = download_video(video_id, video_name)

            if not local_path or not os.path.isfile(local_path):
                raise FileNotFoundError("Downloaded file not found.")

            if os.path.getsize(local_path) <= 0:
                raise ValueError("Downloaded video is empty.")

            # Duplicate check
            digest = file_sha256(local_path)

            if is_duplicate(video_id, digest):
                logger.info("Duplicate skipped: %s", video_name)
                skipped_count += 1
                continue

            # Generate metadata
            metadata = generate_metadata(video_name)

            if not isinstance(metadata, dict):
                raise ValueError("Invalid metadata.")

            for field in ("title", "description", "tags"):
                if field not in metadata:
                    raise ValueError(f"Missing metadata field: {field}")

            if not isinstance(metadata["title"], str) or not metadata["title"].strip():
                raise ValueError("Invalid title.")

            if not isinstance(metadata["description"], str):
                raise ValueError("Invalid description.")

            if not isinstance(metadata["tags"], list):
                raise ValueError("Invalid tags.")

            # Upload exactly one video
            youtube_id = upload_video(local_path, metadata)

            if not youtube_id:
                raise RuntimeError("YouTube upload failed.")

            upload_succeeded = True
            uploaded_count += 1

            logger.info("UPLOAD SUCCESSFUL: %s", youtube_id)
            logger.info(
                "VIDEO URL: https://www.youtube.com/watch?v=%s",
                youtube_id
            )

            # Save upload history
            try:
                record_upload(video, digest, youtube_id)
            except Exception:
                logger.exception(
                    "CRITICAL: Upload succeeded but history save failed. "
                    "Check YouTube and history manually before next run."
                )
                break

            # Save title history
            try:
                commit_title(metadata["title"])
            except Exception:
                logger.exception("Could not save title history.")

        except Exception:
            failed_count += 1

            if upload_succeeded:
                logger.critical(
                    "Upload succeeded but a later operation failed: %s",
                    youtube_id
                )

            logger.exception("VIDEO PROCESSING FAILED: %s", video_name)

        finally:

            if local_path and os.path.isfile(local_path):
                try:
                    os.remove(local_path)
                    logger.info("Temporary file removed.")
                except OSError:
                    logger.warning("Could not remove temporary file.")

    logger.info("=" * 60)
    logger.info("AUTOMATION COMPLETED")
    logger.info("Uploaded this run: %s", uploaded_count)

    try:
        logger.info(
            "Total uploaded today: %s / %s",
            count_uploads_today(),
            DAILY_TOTAL_LIMIT
        )
    except Exception:
        logger.exception("Could not read final daily count.")

    logger.info("Skipped: %s", skipped_count)
    logger.info("Failed: %s", failed_count)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
