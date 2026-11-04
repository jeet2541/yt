
import os
import logging

from src.ai_metadata import generate_metadata
from src.drive_manager import download_video, list_videos

from src.duplicate_checker import (
    file_sha256,
    is_duplicate,
    record_upload
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

DAILY_UPLOAD_LIMIT = int(
    os.getenv("DAILY_UPLOAD_LIMIT", "1")
)


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info("=" * 65)
    logger.info("YOUTUBE SHORTS AUTOMATION STARTED")
    logger.info("=" * 65)

    uploaded_count = 0
    skipped_count = 0
    failed_count = 0

    if DAILY_UPLOAD_LIMIT <= 0:
        logger.warning("Upload limit is zero or negative. Exiting.")
        return

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

    # =====================================================
    # PROCESS VIDEOS
    # =====================================================

    for video in videos:

        if uploaded_count >= DAILY_UPLOAD_LIMIT:
            logger.info("Daily upload limit reached.")
            break

        local_path = None

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

            # -------------------------------------------------
            # 1. DOWNLOAD VIDEO
            # -------------------------------------------------

            logger.info("Downloading original video from Drive...")

            local_path = download_video(
                video_id,
                video_name
            )

            if not local_path or not os.path.isfile(local_path):
                raise FileNotFoundError(
                    "Downloaded video file was not found."
                )

            file_size = os.path.getsize(local_path)

            if file_size <= 0:
                raise ValueError("Downloaded video is empty.")

            logger.info(
                "Download successful. File size: %.2f MB",
                file_size / (1024 * 1024)
            )

            # -------------------------------------------------
            # 2. DUPLICATE CHECK
            # -------------------------------------------------

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

            # -------------------------------------------------
            # 3. GENERATE METADATA
            # -------------------------------------------------

            logger.info("Generating YouTube metadata...")

            metadata = generate_metadata(video_name)

            if not metadata:
                raise ValueError(
                    "Metadata generation returned empty result."
                )

            required_fields = [
                "title",
                "description",
                "tags"
            ]

            for field in required_fields:
                if field not in metadata:
                    raise ValueError(
                        f"Metadata is missing field: {field}"
                    )

            if not metadata["title"]:
                raise ValueError("Video title is empty.")

            logger.info(
                "Selected title: %s",
                metadata["title"]
            )

            logger.info(
                "Description length: %s characters",
                len(metadata["description"])
            )

            logger.info(
                "Tags generated: %s",
                len(metadata["tags"])
            )

            # -------------------------------------------------
            # 4. UPLOAD TO YOUTUBE
            # -------------------------------------------------

            logger.info("Uploading original video to YouTube...")

            youtube_id = upload_video(
                local_path,
                metadata
            )

            if not youtube_id:
                raise RuntimeError(
                    "YouTube upload returned no video ID."
                )

            logger.info(
                "YouTube upload successful. Video ID: %s",
                youtube_id
            )

            # -------------------------------------------------
            # 5. SAVE UPLOAD HISTORY
            # -------------------------------------------------

            logger.info("Saving upload history...")

            record_upload(
                video,
                digest,
                youtube_id
            )

            uploaded_count += 1

            logger.info("=" * 65)
            logger.info("VIDEO COMPLETED SUCCESSFULLY")
            logger.info("Drive file: %s", video_name)
            logger.info("YouTube ID: %s", youtube_id)
            logger.info("=" * 65)

        except Exception:

            failed_count += 1

            logger.exception(
                "VIDEO PROCESSING FAILED: %s",
                video_name
            )

        finally:

            # -------------------------------------------------
            # 6. CLEANUP
            # -------------------------------------------------

            if local_path and os.path.isfile(local_path):

                try:
                    os.remove(local_path)
                    logger.info(
                        "Temporary file removed: %s",
                        video_name
                    )

                except OSError:
                    logger.warning(
                        "Could not remove temporary file: %s",
                        local_path
                    )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    logger.info("")
    logger.info("=" * 65)
    logger.info("YOUTUBE AUTOMATION RUN COMPLETED")
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
