
import json
import logging
import random
import os
from pathlib import Path

logger = logging.getLogger(__name__)

HISTORY_FILE = Path("data/title_history.json")

TITLES = [
    "Lost in the Rhythm",
    "Midnight Dreams",
    "Echoes of Silence",
    "A Sky Full of Memories",
    "Somewhere Beyond the Stars",
    "Fading Into the Night",
    "The Feeling Never Ends",
    "Dreams in Slow Motion",
    "A Moment Called Forever",
    "Where Time Stands Still",
    "Dancing With the Shadows",
    "Memories in Motion",
    "A World Without Noise",
    "Beyond the Horizon",
    "Silence Between the Notes",
    "The Sound of Memories",
    "Chasing Endless Dreams",
    "Lost Somewhere in Time",
    "When the World Sleeps",
    "A Beautiful Escape",
    "Falling Through Memories",
    "Under the Midnight Sky",
    "The Art of Letting Go",
    "Somewhere in Another Life",
    "A Feeling Without Words",
    "Waves of Emotion",
    "The Last Light",
    "A Different Kind of Peace",
    "Dreaming With Open Eyes",
    "Nothing Lasts Forever",
    "Shadows of Yesterday",
    "The Calm Within Chaos",
    "Floating Through Time",
    "A Thousand Silent Thoughts",
    "Beyond What We Know",
    "The Beauty of Silence",
    "One Last Memory",
    "A Place Called Home",
    "The World in Slow Motion",
    "Everything Feels Different",
    "Fading Lights",
    "Endless Night Drive",
    "Somewhere Far Away",
    "Lost in Another Dimension",
    "The Sound of Freedom",
    "Chasing the Moonlight",
    "A Million Little Feelings",
    "The Night We Remember",
    "Dreams Never Fade",
    "A Little Piece of Heaven",
    "Golden Memories",
    "Into the Unknown",
    "The Last Goodbye",
    "Moments We Cannot Repeat",
    "A World of Our Own",
    "Midnight Reflections",
    "Somewhere Between Dreams",
    "The Feeling of Infinity",
    "After the Rain",
    "A Beautiful Kind of Sadness",
    "Beyond the Clouds",
    "Lost in the Atmosphere",
    "The Rhythm of Life",
    "A Quiet Revolution",
    "Stars Above Us",
    "The Other Side of Reality",
    "Time Moves Slowly",
    "The Space Between Us",
    "A Journey Through Sound",
    "Memories That Stay",
    "Into the Blue",
    "When Dreams Become Real",
    "The Endless Summer",
    "A Night to Remember",
    "Echoes From the Past",
    "The World Feels Smaller",
    "A Thousand Miles Away",
    "Nothing But the Moment",
    "Under Electric Skies",
    "The Last Summer Night",
    "Lost Without a Map",
    "The Feeling of Being Alive",
    "A Place Beyond Words",
    "Drifting Through the Night",
    "The Sound of Tomorrow",
    "Another Beautiful Day",
    "A Dream Within a Dream",
    "The Midnight Journey",
    "Where Memories Live",
    "A Moment of Eternity",
    "The Silence We Share",
    "Falling Into Place",
    "A Little More Time",
    "The Universe Within",
    "Somewhere We Belong",
    "The Night Is Young",
    "Beautifully Broken",
    "The Road to Somewhere",
    "A Thousand Dreams Away",
    "The Magic of the Moment",
    "Beyond the Silence",
    "Lost in Your Thoughts",
    "A New Beginning",
    "The Last Horizon",
    "Everything Is Temporary",
    "A World Made of Sound",
    "The Beauty of Letting Go",
    "Through the Endless Night",
    "A Feeling Called Nostalgia",
    "Somewhere in the Universe",
    "The Sound of Yesterday",
    "A Place in the Stars",
    "Dreams After Dark",
    "The Rhythm Never Stops",
    "Time Is Just a Feeling",
    "A Moment in Paradise",
    "Where the Light Begins",
    "Lost in the Memories",
    "The Art of Dreaming",
    "A Different Reality",
    "Nothing Feels the Same",
    "A Sky Without Limits",
    "The Last Piece of Summer",
    "Floating Above the Clouds",
    "A Beautiful Distance",
    "The Night Belongs to Us",
    "Beyond the Ordinary",
    "The Sound of the Ocean",
    "Memories Under Moonlight",
    "A Little Bit of Forever",
    "When Silence Speaks",
    "The Feeling of Yesterday",
    "Somewhere in the Darkness",
    "The World Beyond",
    "A Thousand Broken Stars",
    "Lost Between the Lines",
    "The Beauty of Now",
    "One More Night",
    "The Endless Road",
    "A Moment Outside Time",
    "Dreams in the Distance",
    "The Sound of Midnight",
    "Everything We Never Said",
    "A Universe of Feelings",
    "Where the Night Begins",
    "Chasing Distant Lights",
    "The Last Beautiful Moment",
    "A Different Frequency",
    "Lost in the Sound",
    "The Weight of Memories",
    "A Place Without Time",
    "Beyond Every Boundary",
    "The Sky Remembers",
    "Somewhere After Midnight",
    "A Beautiful Unknown",
    "The Feeling of Home",
    "Dancing Through Time",
    "A Thousand Different Worlds",
    "The Sound of Dreams",
    "Nothing Beyond This Moment",
    "The Other Side of Night",
    "Memories in the Rain",
    "A Little More Magic",
    "The World in Our Eyes",
    "Somewhere We Can Escape",
    "A Night Full of Stars",
    "The Endless Feeling",
    "When Everything Fades",
    "Lost in the Blue",
    "The Art of Being Free",
    "A Beautiful Silence",
    "Beyond the Last Light",
    "The Space of Dreams",
    "Moments Like These",
    "A Story Without Words",
    "The Sound of Forever",
    "Where Time Disappears",
    "A Feeling Worth Keeping",
    "The Midnight Atmosphere",
    "Somewhere Beyond Reality",
    "The Journey Within",
    "A World of Endless Possibilities",
    "The Last Dream",
    "When Stars Align",
    "Nothing But Memories",
    "A Beautiful State of Mind",
    "The Night Feels Different",
    "Lost in Endless Motion",
    "The Soundtrack of Life",
    "A Moment to Breathe",
    "The Beauty of the Unknown",
    "Forever in This Moment",
]


def load_history():
    try:
        if HISTORY_FILE.exists():
            with HISTORY_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, list):
                return data

    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read title history.")

    return []


def save_history(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = HISTORY_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=2, ensure_ascii=False)

    os.replace(temporary_file, HISTORY_FILE)


def generate_random_title():
    history = load_history()

    available = [
        title for title in TITLES
        if title not in history
    ]

    if not available:
        logger.warning("All titles used. Starting a new title cycle.")
        available = TITLES.copy()

    return random.choice(available)


def commit_title(title):
    """Save a title only after its video uploads successfully."""
    if not title:
        return

    history = load_history()

    if title not in history:
        history.append(title)
        save_history(history)
        logger.info("Title added to history: %s", title)


def detect_music_type(filename):
    name = filename.lower()

    categories = {
        "lofi": ["lofi", "lo-fi", "chill", "study"],
        "phonk": ["phonk", "drift", "aggressive"],
        "ambient": ["ambient", "atmosphere", "space"],
        "slowed": ["slowed", "reverb", "slowed-reverb"],
        "remix": ["remix", "edit", "mix"],
        "instrumental": ["instrumental", "piano", "guitar"],
        "electronic": ["edm", "electronic", "synth", "techno"],
    }

    for category, keywords in categories.items():
        if any(keyword in name for keyword in keywords):
            return category

    return "music"


def build_metadata(filename):
    title = generate_random_title()
    music_type = detect_music_type(filename)

    description = (
        f"{title}\n\n"
        "Enjoy the music and let the moment take over.\n"
        "Subscribe for more music and sound experiences.\n\n"
        "#music #shorts #musicshorts #viralshorts"
    )

    tags = [
        "music",
        "music shorts",
        "shorts",
        "viral music",
        "music edit",
        "sound",
        "music vibes",
        music_type,
        "audio",
        "music lovers",
    ]

    logger.info("Music type detected: %s", music_type)
    logger.info("Random title selected: %s", title)

    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags[:15],
    }


def generate_metadata(filename):
    """Fully offline metadata generation."""
    logger.info("Using local music metadata generator.")
    return build_metadata(filename)


def generate_fallback_metadata(filename):
    """Backward compatibility with existing main.py."""
    return build_metadata(filename)
