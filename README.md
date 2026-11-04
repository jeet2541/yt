# Shorts AI Automation

A GitHub Actions-based YouTube Shorts uploader that:
- Reads video files from one Google Drive folder.
- Generates relevant metadata with the Gemini API.
- Checks upload history to avoid re-uploading the same Drive file.
- Uploads up to one video per scheduled run (two runs per day by default).
- Stores upload history in `data/upload_history.json`.

## Important
This project is intended for your own YouTube channel and Google account. Keep OAuth credentials and API keys in GitHub Actions Secrets. Never commit `credentials.json`, `token.json`, or `.env` files.

Google OAuth apps in **Testing** can have refresh tokens that expire after 7 days when non-basic scopes are used. If that happens, generate a fresh token and update the `YOUTUBE_TOKEN_JSON` secret. This project does not bypass Google's OAuth policies.

## Setup overview
1. Create/enable Google Drive API and YouTube Data API v3 in Google Cloud.
2. Create a Desktop OAuth client and authorize the account that owns the YouTube channel and Drive folder.
3. Put the resulting token JSON into the GitHub secret `YOUTUBE_TOKEN_JSON`.
4. Add `DRIVE_FOLDER_ID` and `GEMINI_API_KEY` as repository secrets.
5. Set `YOUTUBE_PRIVACY` to `private` for initial testing.
6. Run **Actions → Shorts AI Automation → Run workflow** manually once.
7. Check the YouTube channel and the Actions logs before relying on the schedule.

## Required GitHub Actions Secrets
- `YOUTUBE_TOKEN_JSON`: complete contents of the OAuth token JSON file.
- `DRIVE_FOLDER_ID`: ID of the Drive folder containing the videos.
- `GEMINI_API_KEY`: Gemini API key.

## Scheduling
The workflow runs at 09:00 and 17:00 India time (UTC 03:30 and 11:30). GitHub scheduled workflows can be delayed. Each run uploads at most one video, for a target of two per day.

## Video folder
Put supported video files directly inside the Drive folder: `.mp4`, `.mov`, `.mkv`, `.webm`.

## Notes
- Initial uploads default to **private**. Change `YOUTUBE_PRIVACY` in the workflow only after successful testing.
- The project currently uses YouTube category `22` (People & Blogs). Change it in `src/youtube_uploader.py` if another category is more appropriate.
- Metadata is generated from the filename and basic video context. It does not watch or understand the actual video content.
- YouTube API quota, OAuth validity, GitHub schedule delays, and Google/Gemini service availability can affect operation.
