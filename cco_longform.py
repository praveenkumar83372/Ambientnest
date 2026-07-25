"""
Dedicated Single-Topic Long-Form Chief Content Officer (CCO) Agent
Generates 10-minute (~1,500 word) laser-focused financial documentaries.
Enforces a single core topic per video with 200 high-impact visual prompts.
"""

import os
import json
from groq import Groq
from channel_state import load_state, get_next_category, log_generated_video, get_topic_history_summary

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

SINGLE_TOPIC_LONGFORM_PROMPT = """
You are the Lead Documentary Writer for 'Ambientnest Wealth' — producing elite 10-minute faceless financial documentaries.

STRICT RULE: SINGLE TOPIC FOCUS ONLY
Do NOT mix multiple unrelated topics into one video. Select ONE specific concept (e.g., 'Warren Buffett's 3 Cash Rules', 'The Math of Saving $100/mo at Age 20 vs 30', or 'How Banks Profit From Credit Card Interest') and explore it in exhaustive depth for the full 10 minutes.

DOCUMENTARY STRUCTURE (1,400 to 1,600 Words Total):
- ACT I: THE HOOK & THE HIDDEN TRUTH (0:00 - 2:30)
- ACT II: THE MECHANICS & PSYCHOLOGY (2:30 - 5:00)
- ACT III: REAL-WORLD CASE STUDIES & EXAMPLES (5:00 - 7:30)
- ACT IV: THE ACTIONABLE BLUEPRINT & LESSONS (7:30 - 10:00)

VISUAL PROMPTS REQUIREMENT:
Provide EXACTLY 200 cinematic 16:9 widescreen visual prompts (1 prompt for every 3-second scene segment across 600 seconds).

STRICT JSON OUTPUT FORMAT ONLY:
{
    "topic": "Single Core Topic",
    "category": "Assigned Strategy Category",
    "title": "The $100,000 Cash Trap: Why Saving Money Is Making You Poorer 🏦",
    "description": "A 10-minute deep dive into the mathematical reality of cash depreciation versus asset accumulation. Learn how top investors protect capital against inflation.\n\nCHAPTERS:\n0:00 - The Cash Illusion\n2:30 - Inflation Math Explained\n5:00 - The Asset Shield Strategy\n7:30 - The 10-Year Wealth Blueprint\n\nSubscribe to @Ambientnest for daily wealth documentaries!\n\n#Ambientnest #WealthDocumentary #SavingMoney #Investing #Finance",
    "tags": ["ambientnest", "wealth documentary", "saving money", "investing", "financial freedom", "compound interest", "rich vs poor", "money mindset"],
    "narration": "Full 1,400 to 1,600 word single-topic script...",
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic aerial shot of massive bank vault with dark aesthetic lighting",
        ... exactly 200 items ...
    ]
}
"""


class SingleTopicLongformOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing!")
        self.client = Groq(api_key=GROQ_API_KEY)

    def generate_documentary_script(self, category=None):
        state = load_state()
        recent_topics = get_topic_history_summary(state, max_items=10)
        
        if not category:
            category = get_next_category(state)

        print(f"\n🎬 [Single-Topic Long-Form Engine] Writing 10-Minute Script for Category: '{category}'")

        user_prompt = f"""
        ASSIGNED CATEGORY: {category}
        RECENT TOPICS TO AVOID: {json.dumps(recent_topics)}

        Instructions: Write a 1,400-1,600 word single-topic documentary script with 200 cinematic visual prompts.
        """

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SINGLE_TOPIC_LONGFORM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            script_payload = json.loads(res.choices[0].message.content)
            narration_text = script_payload.get("narration", "")
            word_count = len(narration_text.split())
            print(f"📊 [Long-Form Engine] Single-topic script generated ({word_count} words).")

            visuals = script_payload.get("visual_prompts", [])
            while len(visuals) < 200:
                visuals.append("Cinematic widescreen dark aesthetic shot of wealth, finance, and trading charts")
            script_payload["visual_prompts"] = visuals[:200]

            log_generated_video(state, script_payload.get("topic", "Wealth Documentary"), category)
            return script_payload

        except Exception as e:
            print(f"❌ Error generating long-form script: {e}")
            raise e