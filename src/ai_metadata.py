import json
import os
from google import genai
from google.genai import types

def generate_metadata(filename):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GitHub Secret GEMINI_API_KEY is missing.")

    client = genai.Client(api_key=api_key)
    prompt = f"""
Create accurate YouTube Shorts metadata using only the filename/context below.
Do not invent facts about footage you have not seen. Avoid clickbait, keyword stuffing,
misleading claims, and unrelated hashtags. Return valid JSON only:
{{
  "title": "engaging, accurate title, max 100 characters",
  "description": "short useful description with a natural call to action if suitable",
  "tags": ["up to 10 relevant tags"]
}}
Video filename/context: {filename}
"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    data = json.loads(response.text)
    title = str(data.get("title", "")).strip()[:100] or filename[:100]
    description = str(data.get("description", "")).strip()
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip()[:100] for tag in tags if str(tag).strip()][:10]
    return {"title": title, "description": description, "tags": tags}
