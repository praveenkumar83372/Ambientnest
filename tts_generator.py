"""
TTS Generator Module
Generates neural voiceover audio using edge-tts.
- Shorts: Single energetic male voice (+12% rate).
- Long-Form Videos: Dynamic Dual-Voice (Male + Female alternating) for documentary depth.
"""

import os
import asyncio
import edge_tts

# Optional dependency for dual-voice audio stitching
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False

# Voice Configs
SHORTS_VOICE = "en-US-AndrewNeural"        # Single energetic male voice for Shorts
LONGFORM_VOICE_MALE = "en-US-AndrewNeural"  # Male voice for facts/data
LONGFORM_VOICE_FEMALE = "en-US-AvaNeural"   # Female voice for narrative/insights


async def generate_audio_and_subtitles(text, audio_out="narration.mp3", srt_out="subtitles.srt"):
    """
    Standard TTS Generator for Shorts (Single Male Voice at +12% pacing).
    """
    communicate = edge_tts.Communicate(text, SHORTS_VOICE, rate="+12%")
    submaker = edge_tts.SubMaker()
    
    with open(audio_out, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub_from_dict(chunk)

    if hasattr(submaker, "get_srt"):
        srt_content = submaker.get_srt()
    elif hasattr(submaker, "generate_subs"):
        srt_content = submaker.generate_subs()
    else:
        srt_content = submaker.generate_vtt()

    with open(srt_out, "w", encoding="utf-8") as srt_file:
        srt_file.write(srt_content)

    print(f"🎙️ [Shorts TTS] Single-voice audio saved to {audio_out} and subtitles to {srt_out}")


async def generate_longform_dual_voice(segments, audio_out="longform_narration.mp3", srt_out="longform_subtitles.srt"):
    """
    Dual-Voice TTS Generator for 10+ Minute Long-Form Documentaries.
    Takes a list of segmented dictionaries containing speaker and text:
    [
        {"speaker": "MALE", "text": "In 1929, the global banking system experienced a shift..."},
        {"speaker": "FEMALE", "text": "Behind closed doors, the top 1% were already reallocating capital..."}
    ]
    """
    print(f"\n🎭 [Long-Form TTS] Generating dual-voice narration ({len(segments)} segments)...")
    
    temp_audio_files = []
    combined_audio = AudioSegment.empty() if HAS_PYDUB else None
    all_srt_blocks = []
    current_time_offset_ms = 0

    for idx, seg in enumerate(segments):
        speaker = seg.get("speaker", "MALE").upper()
        text = seg.get("text", "").strip()

        if not text:
            continue

        voice = LONGFORM_VOICE_MALE if speaker == "MALE" else LONGFORM_VOICE_FEMALE
        temp_mp3 = f"temp_seg_{idx}.mp3"
        
        # Long-form uses normal pacing (+0% to +4%) for natural documentary tone
        communicate = edge_tts.Communicate(text, voice, rate="+4%")
        submaker = edge_tts.SubMaker()

        with open(temp_mp3, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.create_sub_from_dict(chunk)

        if HAS_PYDUB:
            seg_audio = AudioSegment.from_mp3(temp_mp3)
            combined_audio += seg_audio
            temp_audio_files.append(temp_mp3)

        if hasattr(submaker, "get_srt"):
            all_srt_blocks.append(submaker.get_srt())

    if HAS_PYDUB and combined_audio:
        combined_audio.export(audio_out, format="mp3")
        for tmp in temp_audio_files:
            if os.path.exists(tmp):
                os.remove(tmp)
        print(f"✅ Dual-voice master audio compiled successfully: {audio_out}")
    else:
        print("⚠️ pydub not installed. Please install pydub to enable audio stitching.")

    # Save combined SRT subtitles
    with open(srt_out, "w", encoding="utf-8") as f:
        f.write("\n\n".join(all_srt_blocks))

    print(f"📝 Dual-voice subtitles saved to {srt_out}")
    return audio_out, srt_out


if __name__ == "__main__":
    # Test Shorts Single-Voice Generator
    asyncio.run(generate_audio_and_subtitles("Welcome to Ambientnest. Here are the top wealth secrets of the elite."))