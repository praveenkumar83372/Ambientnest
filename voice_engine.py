"""
Voice selection engine.
Maps content slot voice keys to Edge TTS voices with the right rate and style.
Each content category gets a distinct voice for variety and authenticity.
"""

import edge_tts

# voice key → (edge_tts_voice, rate, description)
VOICE_MAP = {
    "christopher": ("en-US-ChristopherNeural", "+0%",  "Deep, authoritative — Finance/Economics"),
    "guy":         ("en-US-GuyNeural",         "+4%",  "Energetic, forward — AI/Tech"),
    "ryan":        ("en-GB-RyanNeural",        "+0%",  "British documentary — History"),
    "eric":        ("en-US-EricNeural",        "+2%",  "Gravitas and wonder — Science/Space"),
    "aria":        ("en-US-AriaNeural",        "+3%",  "Curious and warm — Culture/Facts"),
}

DEFAULT_VOICE = "christopher"


async def generate_voiceover(text, output_path, voice_key=DEFAULT_VOICE):
    """Generate a voiceover MP3 using the voice for this slot's category."""
    voice_name, rate, desc = VOICE_MAP.get(voice_key, VOICE_MAP[DEFAULT_VOICE])
    communicate = edge_tts.Communicate(text, voice_name, rate=rate)
    await communicate.save(output_path)


def get_voice_info(voice_key):
    return VOICE_MAP.get(voice_key, VOICE_MAP[DEFAULT_VOICE])