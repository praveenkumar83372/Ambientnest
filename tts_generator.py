"""
TTS Generator Module
Generates neural voiceover audio and timing subtitles using edge-tts.
"""

import asyncio
import edge_tts

# Deep, energetic male voice ideal for finance content
VOICE = "en-US-AndrewNeural"

async def generate_audio_and_subtitles(text, audio_out="narration.mp3", srt_out="subtitles.srt"):
    communicate = edge_tts.Communicate(text, VOICE, rate="+5%")
    submaker = edge_tts.SubMaker()
    
    with open(audio_out, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub_from_dict(chunk)

    # Use get_srt() or generate_subs() dynamically depending on edge-tts version
    if hasattr(submaker, "get_srt"):
        srt_content = submaker.get_srt()
    elif hasattr(submaker, "generate_subs"):
        srt_content = submaker.generate_subs()
    else:
        # Fallback to webvtt format if needed
        srt_content = submaker.generate_vtt()

    with open(srt_out, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)

    print(f"🎙️ Voiceover saved to {audio_out} and subtitles to {srt_out}")

if __name__ == "__main__":
    asyncio.run(generate_audio_and_subtitles("Test narration text for finance shorts."))