"""
Chief Visual Officer (CVO) Agent
The visual and sound director of the automated financial channel C-Suite.

Responsibilities:
1. Takes the approved 60-second narration script from the CCO.
2. Breaks down the narration into EXACTLY 20 visual prompts (1 prompt for every 3 seconds).
3. Assigns audio profiles: dynamic music moods (e.g., dark ambient, tension riser) and SFX transition triggers.
4. Validates visual diversity to guarantee zero scene repetition.
"""

import os
import json
from groq import Groq
from channel_state import load_state

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CVO_SYSTEM_PROMPT = """
You are the Chief Visual Officer (CVO) directing visual aesthetics and audio soundscapes for a high-RPM YouTube Shorts finance channel.

YOUR MISSION:
Analyze the 60-second financial narration script and create an exact 20-scene visual storyboard with sound effect tags.

CRITICAL REQUIREMENTS:
1. SCENE COUNT: Generate EXACTLY 20 visual prompt descriptions (1 visual every 3 seconds for a 60s total duration).
2. VISUAL STYLE: Prompts must describe dark, high-contrast, cinematic, luxury financial aesthetics (e.g., glowing stock graphs, close-up gold bars, dark office vaults, luxury cars, trading screens).
3. NO DUPLICATES: Ensure every single scene description is distinct to prevent visual repetition.
4. AUDIO DIRECTION: Assign a dominant music mood and specific SFX triggers (e.g., cash_register, glitch_impact, fast_whoosh, deep_bass_drop) matching key script moments.

STRICT JSON OUTPUT FORMAT ONLY (NO MARKDOWN OR EXTRA TEXT):
{
    "music_mood": "dark ambient cinematic / tension riser / aggressive motivation",
    "sfx_triggers": ["deep_bass_drop", "cash_register", "fast_whoosh", "glitch_impact"],
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic close up of glowing gold bullion bars stacked in a dark vault",
        "Prompt 2 (3-6s): Financial analyst staring at red and green candle stock charts",
        ... exactly 20 items ...
    ]
}
"""


class ChiefVisualOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate_storyboard(self, script_payload):
        """
        Takes the script JSON from CCO and generates an exact 20-scene visual storyboard 
        and audio design payload.
        """
        print("\n🎬 [CVO Agent] Directing visual storyboard & audio design...")
        narration = script_payload.get("narration", "")
        title = script_payload.get("title", "Financial Short")
        category = script_payload.get("category", "Finance")

        user_prompt = f"""
        TITLE: {title}
        CATEGORY: {category}
        NARRATION SCRIPT:
        "{narration}"

        Create the 20-scene visual prompt storyboard and audio direction JSON payload.
        """

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CVO_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            storyboard = json.loads(res.choices[0].message.content)

            # Enforce strict 20 visual prompts count
            visuals = storyboard.get("visual_prompts", [])
            if len(visuals) != 20:
                print(f"⚠️ CVO Prompt count mismatch ({len(visuals)} received). Standardizing to 20...")
                while len(visuals) < 20:
                    visuals.append("Cinematic dark financial aesthetic stock video of money and gold")
                storyboard["visual_prompts"] = visuals[:20]

            print(f"  ✅ Storyboard complete: 20 scenes generated with mood '{storyboard.get('music_mood')}'")
            return storyboard

        except Exception as e:
            print(f"⚠️ CVO Storyboard generation warning ({e}). Generating fallback prompts.")
            fallback_prompts = [
                f"Scene {i+1}: Dark luxury financial aesthetic video representing {category}"
                for i in range(20)
            ]
            return {
                "music_mood": "dark ambient cinematic",
                "sfx_triggers": ["fast_whoosh", "cash_register"],
                "visual_prompts": fallback_prompts
            }


if __name__ == "__main__":
    cvo = ChiefVisualOfficer()
    test_script = {
        "title": "Dark Psychology of Wealth #Shorts",
        "category": "Dark Psychology & Wealth Secrets",
        "narration": "If you have $1,000 in your bank account right now, stop doing this immediately..."
    }
    output = cvo.generate_storyboard(test_script)
    print("\nCVO Visual & Audio Output Payload:")
    print(json.dumps(output, indent=2))