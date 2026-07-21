"""
TTS Generator Module
Generates neural voiceover audio at +12% energy pacing and accurate word-level 
timing subtitles using edge-tts.
"""

import asyncio
import edge_tts

# Deep, energetic male professional voice ideal for wealth & finance content
VOICE = "en-US-AndrewNeural"

async def generate_audio_and_subtitles(text, audio_out="narration.mp3", srt_out="subtitles.srt"):
    """
    Generates neural voiceover speech with energetic +12% rate pacing 
    and outputs synchronized SRT subtitle files.
    """
    # Set rate to +12% for fast, gripping short-form pacing
    communicate = edge_tts.Communicate(text, VOICE, rate="+12%")
    submaker = edge_tts.SubMaker()
    
    with open(audio_out, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub_from_dict(chunk)

    # Safely extract SRT contents across various edge-tts library versions
    if hasattr(submaker, "get_srt"):
        srt_content = submaker.get_srt()
    elif hasattr(submaker, "generate_subs"):
        srt_content = submaker.generate_subs()
    else:
        # Fallback format conversion if needed
        srt_content = submaker.generate_vtt()

    with open(srt_out, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)

    print(f"🎙️ High-energy voiceover saved to {audio_out} and synchronized subtitles to {srt_out}")

if __name__ == "__main__":
    asyncio.run(generate_audio_and_subtitles("Welcome to Ambientnest. Here are the top wealth secrets of the elite."))