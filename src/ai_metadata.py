
import json
import os
import time
import hashlib
import re
import urllib.request
import urllib.error

from google import genai
from google.genai import types


# =========================================================
# AESTHETIC CAPTION BANK - LOCAL BACKUP
# =========================================================

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


PROMPT_TEMPLATE = """
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
{
  "title": "A unique aesthetic title",
  "description": "A short description with hashtags",
  "tags": ["tag1", "tag2", "tag3"]
}

Video filename/context: {filename}
"""


# =========================================================
# HELPERS
# =========================================================

def detect_category(filename):
    name = filename.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(word in name for word in keywords):
            return category

    return "dream"


def parse_metadata(text, filename):
    if not text:
        raise ValueError("AI returned empty response.")

    text = text.strip()

    # Remove Markdown code fences if present.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    data = json.loads(text)

    title = str(data.get("title", "")).strip()[:100]
    description = str(data.get("description", "")).strip()
    tags = data.get("tags", [])

    if not title:
        raise ValueError("AI did not generate a title.")

    if not isinstance(tags, list):
        tags = []

    tags = [
        str(tag).strip()[:100]
        for tag in tags
        if str(tag).strip()
    ][:10]

    return {
        "title": title,
        "description": description,
        "tags": tags
    }


def generate_fallback_metadata(filename):
    """Generate metadata locally without any API."""

    category = detect_category(filename)
    captions = CAPTIONS[category]

    file_hash = hashlib.sha256(
        filename.encode("utf-8")
    ).hexdigest()

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


# =========================================================
# GEMINI - DISCOVER AVAILABLE GENERATION MODELS
# =========================================================

def get_gemini_models(client):
    models = []

    for model in client.models.list():
        name = getattr(model, "name", None)

        if not name:
            continue

        model_id = name.replace("models/", "")

        if not model_id.startswith("gemini-"):
            continue

        # Skip non-text-generation model families.
        excluded = (
            "embedding",
            "image",
            "tts",
            "audio",
            "veo",
            "robotics",
            "computer-use"
        )

        if any(word in model_id.lower() for word in excluded):
            continue

        actions = (
            getattr(model, "supported_actions", None)
            or getattr(model, "supported_generation_methods", None)
        )

        # If the API exposes supported actions, verify generateContent.
        if actions:
            if not any("generatecontent" in str(a).lower() for a in actions):
                continue

        models.append(model_id)

    # Try Flash models first, then other eligible Gemini models.
    models = sorted(
        set(models),
        key=lambda x: (
            "flash" not in x.lower(),
            x.lower()
        )
    )

    return models


def try_gemini(filename):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY missing. Skipping Gemini.")
        return None

    try:
        client = genai.Client(api_key=api_key)
        models = get_gemini_models(client)

        print(f"Gemini models discovered: {len(models)}")

    except Exception as error:
        print(f"Could not list Gemini models: {error}")
        return None

    if not models:
        print("No eligible Gemini models found.")
        return None

    prompt = PROMPT_TEMPLATE.format(filename=filename)

    for model_id in models:
        try:
            print(f"Trying Gemini model: {model_id}")

            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.9
                )
            )

            result = parse_metadata(response.text, filename)

            print(f"Gemini SUCCESS: {model_id}")
            return result

        except Exception as error:
            print(f"Gemini model failed: {model_id} | {error}")
            continue

    print("All eligible Gemini models failed.")
    return None


# =========================================================
# GROQ - LIVE MODEL DISCOVERY + FALLBACK
# =========================================================

def groq_request(api_key, endpoint, method="GET", payload=None):
    url = "https://api.groq.com/openai/v1/" + endpoint

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = None

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def try_groq(filename):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        print("GROQ_API_KEY missing. Skipping Groq.")
        return None

    try:
        model_data = groq_request(api_key, "models")
        available_models = model_data.get("data", [])

        # Exclude audio, moderation and other non-chat model families.
        excluded = (
            "whisper",
            "guard",
            "speech",
            "audio",
            "distil"
        )

        models = [
            item.get("id")
            for item in available_models
            if item.get("id")
            and item.get("active", True)
            and not any(
                word in item.get("id", "").lower()
                for word in excluded
            )
        ]

        preferred = os.getenv("GROQ_MODEL")

        if preferred and preferred in models:
            models.remove(preferred)
            models.insert(0, preferred)

        print(f"Groq chat model candidates: {len(models)}")

    except Exception as error:
        print(f"Could not list Groq models: {error}")
        return None

    prompt = PROMPT_TEMPLATE.format(filename=filename)

    for model_id in models:
        try:
            print(f"Trying Groq model: {model_id}")

            result = groq_request(
                api_key,
                "chat/completions",
                method="POST",
                payload={
                    "model": model_id,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Return valid JSON only. Do not use Markdown."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.9,
                    "max_tokens": 500,
                    "response_format": {
                        "type": "json_object"
                    }
                }
            )

            content = result["choices"][0]["message"]["content"]
            metadata = parse_metadata(content, filename)

            print(f"Groq SUCCESS: {model_id}")
            return metadata

        except Exception as error:
            print(f"Groq model failed: {model_id} | {error}")
            continue

    print("All eligible Groq models failed.")
    return None


# =========================================================
# MAIN PROVIDER ROUTER
# GEMINI -> GROQ -> LOCAL BACKUP
# =========================================================

def generate_metadata(filename):

    print("\n========================================")
    print("AI METADATA GENERATION STARTED")
    print("========================================")

    # First: Try all eligible Gemini models.
    result = try_gemini(filename)

    if result:
        return result

    # Second: Try available Groq chat models.
    print("\nSwitching to Groq...")
    result = try_groq(filename)

    if result:
        return result

    # Final: Generate metadata locally.
    print("\nBoth AI providers failed.")
    print("Using local aesthetic caption backup.")

    return generate_fallback_metadata(filename)
