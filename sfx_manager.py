"""
sfx_manager.py
Maps the sfx tags Gemini writes into scene['sfx'] to actual audio files in
assets/sfx/. Falls back gracefully if a requested tag has no matching file
so the pipeline never crashes over a missing sound.

Drop your own royalty-free / licensed sfx files into assets/sfx/ using the
filenames below (or edit SFX_LIBRARY to point at whatever you have).
"""

from pathlib import Path

SFX_DIR = Path(__file__).parent / "assets" / "sfx"

SFX_LIBRARY = {
    "birdsong": "birdsong_morning.mp3",
    "kettle boiling": "kettle_boil.mp3",
    "rain": "rain_soft.mp3",
    "heavy rain": "rain_heavy.mp3",
    "wind": "wind_gentle.mp3",
    "footsteps wood floor": "footsteps_wood.mp3",
    "footsteps gravel": "footsteps_gravel.mp3",
    "pottery wheel": "pottery_wheel.mp3",
    "kiln crackle": "kiln_crackle.mp3",
    "ceramic crack": "ceramic_crack.mp3",
    "cicadas": "cicadas_summer.mp3",
    "waves": "waves_shore.mp3",
    "cat meow": "cat_meow.mp3",
    "coins jar": "coins_jar.mp3",
    "page turn": "page_turn.mp3",
    "chopping vegetables": "chopping_veg.mp3",
    "simmering pot": "simmer_pot.mp3",
    "temple bell": "temple_bell.mp3",
    "cherry blossoms falling": "petals_wind.mp3",
    "train distant": "train_distant.mp3",
    "quiet room tone": "room_tone_quiet.mp3",
}

DEFAULT_AMBIENCE = "room_tone_quiet.mp3"


def resolve_sfx(tags: list[str]) -> list[Path]:
    """Turn a list of free-text sfx tags from the story into real file paths."""
    resolved = []
    for tag in tags or []:
        filename = SFX_LIBRARY.get(tag.strip().lower())
        if filename:
            path = SFX_DIR / filename
            if path.exists():
                resolved.append(path)
    return resolved


def ambience_for_season_weather(season: str, weather_description: str) -> Path | None:
    """Picks one background ambience track to loop under a whole video."""
    desc = weather_description.lower()
    if "rain" in desc or "drizzle" in desc:
        return SFX_DIR / SFX_LIBRARY["heavy rain" if "heavy" in desc else "rain"]
    if "summer" in season:
        return SFX_DIR / SFX_LIBRARY["cicadas"]
    if "wind" in desc:
        return SFX_DIR / SFX_LIBRARY["wind"]
    fallback = SFX_DIR / DEFAULT_AMBIENCE
    return fallback if fallback.exists() else None


def missing_assets_report() -> list[str]:
    """Utility to check which sfx files still need to be sourced/dropped in."""
    return [
        filename for filename in sorted(set(SFX_LIBRARY.values()))
        if not (SFX_DIR / filename).exists()
    ]


if __name__ == "__main__":
    missing = missing_assets_report()
    print(f"{len(missing)} sfx files missing from {SFX_DIR}:")
    for m in missing:
        print(" -", m)
