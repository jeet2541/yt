
import os
import logging

from src.ai_metadata import generate_metadata, commit_title
from src.drive_manager import download_video, list_videos

from src.duplicate_checker import (
    file_sha256,
    is_duplicate,
    record_upload,
)

from src.youtube_uploader import upload_video


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)


# =========================================================
# SETTINGS
# =========================================================

DAILY_UPLOAD_LIMIT = int(os.getenv("DAILY_UPLOAD_LIMIT", "1"))


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info("=" * 65)
    logger.info("YOUTUBE MUSIC AUTOMATION STARTED")
    logger.info("=" * 65)

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    if DAILY_UPLOAD_LIMIT <= 0:
        logger.warning("Upload limit is zero or negative. Exiting.")
        return

    # -----------------------------------------------------
    # GET VIDEOS FROM GOOGLE DRIVE
    # -----------------------------------------------------

    try:
        videos = list_videos()

    except Exception:
        logger.exception("Could not retrieve videos from Google Drive.")
        return

    if not videos:
        logger.info("No videos found in Google Drive.")
        return

    logger.info("Videos found: %s", len(videos))
    logger.info("Daily upload limit: %s", DAILY_UPLOAD_LIMIT)

    # -----------------------------------------------------
    # PROCESS VIDEOS
    # -----------------------------------------------------

    for video in videos:

        if uploaded_count >= DAILY_UPLOAD_LIMIT:
            logger.info("Daily upload limit reached.")
            break

        local_path = None
        upload_succeeded = False

        video_name = video.get("name", "Unknown video")
        video_id = video.get("id")

        try:

            if not video_id:
                logger.warning(
                    "Skipping video with missing Drive ID: %s",
                    video_name
                )
                skipped_count += 1
                continue

            logger.info("-" * 65)
            logger.info("PROCESSING: %s", video_name)

            # 1. DOWNLOAD ORIGINAL VIDEO

            logger.info("Downloading original video from Drive...")

            local_path = download_video(video_id, video_name)

            if not local_path or not os.path.isfile(local_path):
                raise FileNotFoundError(
                    "Downloaded video file was not found."
                )

            file_size = os.path.getsize(local_path)

            if file_size <= 0:
                raise ValueError("Downloaded video is empty.")

            logger.info(
                "Download successful: %.2f MB",
                file_size / (1024 * 1024)
            )

            # 2. DUPLICATE CHECK

            logger.info("Checking duplicate status...")

            digest = file_sha256(local_path)

            if is_duplicate(video_id, digest):
                logger.info(
                    "Duplicate detected. Skipping: %s",
                    video_name
                )
                skipped_count += 1
                continue

            logger.info("Video is not a duplicate.")

            # 3. GENERATE METADATA

            logger.info("Generating music metadata...")

            metadata = generate_metadata(video_name)

            if not isinstance(metadata, dict):
                raise ValueError("Invalid metadata response.")

            for field in ("title", "description", "tags"):
                if field not in metadata:
                    raise ValueError(
                        f"Metadata is missing field: {field}"
                    )

            if not metadata["title"]:
                raise ValueError("Video title is empty.")

            logger.info("Selected title: %s", metadata["title"])
            logger.info("Tags generated: %s", len(metadata["tags"]))

            # 4. UPLOAD TO YOUTUBE

            logger.info("Uploading original video to YouTube...")

            youtube_id = upload_video(local_path, metadata)

            if not youtube_id:
                raise RuntimeError(
                    "YouTube upload returned no video ID."
                )

            upload_succeeded = True

            logger.info(
                "YouTube upload successful: %s",
                youtube_id
            )

            # 5. SAVE UPLOAD HISTORY

            logger.info("Saving upload history...")

            record_upload(video, digest, youtube_id)

            # 6. SAVE TITLE HISTORY ONLY AFTER SUCCESS

            commit_title(metadata["title"])

            uploaded_count += 1

            logger.info(
                "VIDEO COMPLETED SUCCESSFULLY: https://www.youtube.com/watch?v=%s",
                youtube_id
            )

        except Exception:

            failed_count += 1

            if upload_succeeded:
                logger.critical(
                    "Video was uploaded, but history saving failed. "
                    "YouTube ID: %s | Drive ID: %s. "
                    "Check upload history before rerunning.",
                    youtube_id,
                    video_id
                )

            logger.exception(
                "VIDEO PROCESSING FAILED: %s",
                video_name
            )

        finally:

            # 7. CLEANUP

            if local_path and os.path.isfile(local_path):

                try:
                    os.remove(local_path)
                    logger.info("Temporary file removed.")

                except OSError:
                    logger.warning(
                        "Could not remove temporary file: %s",
                        local_path
                    )

    # -----------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------

    logger.info("")
    logger.info("=" * 65)
    logger.info("YOUTUBE MUSIC AUTOMATION COMPLETED")
    logger.info("=" * 65)

    logger.info("Total videos found: %s", len(videos))
    logger.info("Successfully uploaded: %s", uploaded_count)
    logger.info("Skipped videos: %s", skipped_count)
    logger.info("Failed videos: %s", failed_count)

    logger.info("=" * 65)


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    main()
