
import json
import os
import time

from google import genai
from google.genai import types


def generate_metadata(filename):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GitHub Secret GEMINI_API_KEY is missing."
        )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an expert YouTube Shorts metadata creator
specializing in aesthetic, dreamy and cinematic visual content.

YOUR WRITING STYLE:
Use the style of these aesthetic caption examples:

- Where the sky turns gold and time slows down.
- Somewhere between the sunset and a dream.
- Lost somewhere in the colors of the evening.
- Where turquoise waters meet endless horizons.
- Somewhere between midnight and magic.
- The moon makes even silence feel beautiful.
- A little mist, a little magic, and endless green.
- Where the forest keeps its secrets.
- Some journeys are better without a destination.
- Chasing horizons, one road at a time.
- Above the clouds, closer to the stars.
- Somewhere between imagination and reality.
- A moment that feels too beautiful to be real.
- Escaping reality, one beautiful frame at a time.

CONTENT CATEGORIES:
1. Sunset and golden hour
2. Ocean, beaches and tropical escapes
3. Moonlight, stars and night aesthetics
4. Forests, nature and misty landscapes
5. Roads, travel and cinematic moments
6. Mountains, clouds and dreamy places
7. AI-generated dreamy photography

TITLE RULES:
- Create a unique, beautiful and memorable title.
- Use poetic, emotional and cinematic wording.
- Keep the title natural and attractive.
- Prefer approximately 5-12 words.
- Maximum 100 characters.
- Emojis are optional. Use them sparingly.
- Do not copy example captions word-for-word.
- Avoid boring generic titles.
- Avoid clickbait and misleading claims.

DESCRIPTION RULES:
- Write a short aesthetic description.
- Match the topic and mood of the filename.
- Add a natural engagement line when appropriate.
- Add 2-3 relevant hashtags at the end.
- Do not add unrelated hashtags.

TAGS RULES:
- Generate up to 10 relevant YouTube search tags.
- Include topic-specific and aesthetic keywords.
- Do not repeat keywords unnecessarily.
- Do not use unrelated trending keywords.

ACCURACY:
- You can only see the filename/context, not the actual video.
- Never invent specific locations, objects or events.
- If the filename is vague, create a general aesthetic title
  without claiming details that are not provided.

Return valid JSON only, with this exact structure:
{{
    "title": "Your unique aesthetic title",
    "description": "Short relevant description with hashtags",
    "tags": ["tag1", "tag2", "tag3"]
}}

VIDEO FILENAME/CONTEXT:
{filename}
"""

    response = None

    # Retry temporary Gemini server and rate-limit errors.
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            break

        except Exception as error:
            error_code = getattr(error, "code", None)

            if error_code not in (429, 500, 502, 503, 504):
                raise

            if attempt == 3:
                raise

            wait_time = 10 * (2 ** attempt)

            print(
                f"Gemini temporarily unavailable. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    if response is None or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    try:
        data = json.loads(response.text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Gemini returned invalid JSON metadata."
        ) from error

    title = str(data.get("title", "")).strip()[:100]
    description = str(data.get("description", "")).strip()

    tags = data.get("tags", [])

    if not isinstance(tags, list):
        tags = []

    tags = [
        str(tag).strip()[:100]
        for tag in tags
        if str(tag).strip()
    ][:10]

    return {
        "title": title or filename[:100],
        "description": description,
        "tags": tags
    }
