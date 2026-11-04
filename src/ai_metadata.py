
import json
import os
import time
import hashlib
import re

from google import genai
from google.genai import types


# Aesthetic caption bank inspired by your 100 examples.
CAPTIONS = {
    "sunset": [
        "Where the sky turns gold and time slows down.",
        "Chasing the last light of a beautiful day.",
        "Somewhere between the sunset and a dream.",
        "Golden skies and moments that last forever.",
        "Lost somewhere in the colors of the evening.",
        "Every sunset brings its own kind of peace."
    ],
    "ocean": [
        "Somewhere between the waves and the wild.",
        "Let the ocean take you somewhere peaceful.",
        "Where turquoise waters meet endless horizons.",
        "The sound of waves is all the music I need.",
        "Finding peace where the land meets the sea."
    ],
    "night": [
        "Somewhere between midnight and magic.",
        "The moon makes even silence feel beautiful.",
        "A thousand stars and a million little dreams.",
        "When the world sleeps, the sky comes alive.",
        "A dream painted across the midnight sky."
    ],
    "forest": [
        "Where the forest keeps its secrets.",
        "A little mist, a little magic, and endless green.",
        "Somewhere nature forgot to be ordinary.",
        "Hidden between the trees and the clouds.",
        "A peaceful corner of a restless world."
    ],
    "road": [
        "Some journeys are better without a destination.",
        "Chasing horizons, one road at a time.",
        "Sometimes the journey is the destination.",
        "Somewhere between leaving and arriving.",
        "A quiet drive through a beautiful dream."
    ],
    "mountain": [
        "Above the clouds, closer to the stars.",
        "Where the mountains touch the morning sky.",
        "Somewhere the clouds feel like home.",
        "The mountains are calling in their own quiet way.",
        "Between the mountains and the endless blue."
    ],
    "dream": [
        "Somewhere between imagination and reality.",
        "A moment that feels too beautiful to be real.",
        "Escaping reality, one beautiful frame at a time.",
        "A beautiful escape from the ordinary.",
        "Where reality fades and imagination begins."
    ],
}


CATEGORY_KEYWORDS = {
    "sunset": ["sunset", "sunrise", "golden", "evening", "dusk", "sky"],
    "ocean": ["ocean", "sea", "beach", "wave", "water", "coast", "tropical"],
    "night": ["moon", "night", "star", "midnight", "galaxy", "space"],
    "forest": ["forest", "tree", "nature", "green", "mist", "jungle"],
    "road": ["road", "drive", "car", "travel", "journey", "highway"],
    "mountain": ["mountain", "cloud", "hill", "snow", "peak"],
}


def detect_category(filename):
    name = filename.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(word in name for word in keywords):
            return category

    return "dream"


def generate_fallback_metadata(filename):
    """Generate metadata locally when Gemini is unavailable."""

    category = detect_category(filename)
    captions = CAPTIONS[category]

    # Select a repeatable caption based on the filename.
    file_hash = hashlib.sha256(filename.encode("utf-8")).hexdigest()
    index = int(file_hash[:8], 16) % len(captions)

    title = captions[index]

    clean_name = re.sub(
        r"[_\-.]+",
        " ",
        os.path.splitext(filename)[0]
    ).strip()

    descriptions = {
        "sunset": "A peaceful moment filled with golden skies and beautiful colors.",
        "ocean": "Escape into the calm beauty of waves, water and endless horizons.",
        "night": "A dreamy night atmosphere beneath a beautiful sky.",
        "forest": "Find a little peace in the beauty of nature and quiet landscapes.",
        "road": "A cinematic journey through beautiful roads and unforgettable moments.",
        "mountain": "A peaceful escape into the beauty of mountains and clouds.",
        "dream": "A beautiful aesthetic moment somewhere between imagination and reality."
    }

    tag_groups = {
        "sunset": ["sunset", "golden hour", "sunset aesthetic", "beautiful sky"],
        "ocean": ["ocean", "beach aesthetic", "ocean waves", "tropical"],
        "night": ["night aesthetic", "moonlight", "stars", "dreamy night"],
        "forest": ["forest aesthetic", "nature", "green landscape", "misty forest"],
        "road": ["cinematic drive", "travel aesthetic", "beautiful roads", "journey"],
        "mountain": ["mountains", "clouds", "mountain aesthetic", "nature views"],
        "dream": ["aesthetic", "dreamy visuals", "cinematic", "beautiful scenery"]
    }

    tags = tag_groups[category] + [
        "aesthetic shorts",
        "relaxing visuals",
        "cinematic shorts"
    ]

    description = descriptions[category]

    if clean_name:
        description += f" Video theme: {clean_name}."

    description += "\n\nEnjoy the view and take a moment to relax."
    description += "\n#aesthetic #shorts #cinematic"

    return {
        "title": title[:100],
        "description": description,
        "tags": tags[:10]
    }


def generate_metadata(filename):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
You create beautiful YouTube Shorts metadata for aesthetic,
dreamy and cinematic visual content.

STYLE EXAMPLES:
- Where the sky turns gold and time slows down.
- Somewhere between the sunset and a dream.
- Where turquoise waters meet endless horizons.
- Somewhere between midnight and magic.
- Where the forest keeps its secrets.
- Some journeys are better without a destination.
- Above the clouds, closer to the stars.
- Somewhere between imagination and reality.

Create a UNIQUE title inspired by this writing style.
Do not copy examples word-for-word.

Rules:
- Title: poetic, attractive, maximum 100 characters.
- Description: short, relevant and natural.
- Add 2-3 relevant hashtags in description.
- Tags: up to 10 relevant YouTube tags.
- Avoid clickbait and keyword stuffing.
- Do not invent details about footage you cannot see.
- Use the filename only as context.

Return valid JSON only:
{{
  "title": "A unique aesthetic title",
  "description": "A short description with hashtags",
  "tags": ["tag1", "tag2", "tag3"]
}}

Video filename/context: {filename}
"""

    response = None

    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
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
                f"Gemini unavailable. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    if response is None or not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    data = json.loads(response.text)

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
