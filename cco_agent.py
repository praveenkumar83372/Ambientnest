"""
Chief Content Officer (CCO) Agent
Generates high-retention, 60-second viral scripts for YouTube Shorts using Groq API.

Responsibilities:
1. Brainstorms and pitches novel content concepts to the CEO.
2. Reads shared memory (channel_state.json) to learn from past video metrics and feedback.
3. Writes high-hook 130-150 word narration scripts.
4. Generates EXACTLY 20 scene descriptions (1 every 3 seconds) for the Visual Engine.
5. Produces SEO titles, descriptions, and tag metadata.
"""

import os
import json
from groq import Groq
from channel_state import load_state, get_next_category, log_generated_video, get_topic_history_summary, save_state

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CCO_SCRIPT_PROMPT = """
You are the Chief Content Officer (CCO) of a high-RPM faceless YouTube Shorts channel focused on Wealth, Money, and Finance.

YOUR MISSION:
Write a fast-paced, high-stakes, high-retention 60-second video script (~130-150 words spoken narration).

CRITICAL REQUIREMENTS:
1. HOOK: First 3 seconds must grab instant attention (shocking dark truth, bold financial claim, high stakes).
2. VISUAL PROMPTS: Provide EXACTLY 20 distinct visual scene descriptions (1 visual prompt for every 3-second scene).
3. ANTI-REPEAT: Do NOT re-use ideas from recent topic history.
4. METADATA: Generate a viral title (<70 chars ending with #Shorts), a high-conversion description, and 20 SEO tags.

STRICT JSON OUTPUT FORMAT ONLY (NO MARKDOWN OR EXTRA TEXT):
{
    "topic": "Core topic title",
    "category": "Assigned strategy category",
    "title": "Shocking Title Here #Shorts",
    "description": "Engaging description summarizing key takeaways. Subscribe for daily wealth strategies! #Shorts #Finance #Money #Wealth #Investing",
    "tags": ["finance", "money", "wealth", "business", "investing", "dark psychology", "passive income", "shorts"],
    "narration": "Full 60-second continuous voiceover text here...",
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic close up of luxury gold bars in dark lighting",
        "Prompt 2 (3-6s): Financial trader looking at glowing stock charts",
        ... exactly 20 items ...
    ]
}
"""

CCO_PITCH_PROMPT = """
You are the CCO suggesting a brand-new, out-of-the-box financial topic concept to the CEO.
Based on recent topic history and current financial trends, suggest a viral video concept that maximizes watch time.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "proposed_topic": "Unique concept title",
    "concept_pitch": "Why this will go viral and command high RPM",
    "target_category": "Category name or sub-niche"
}
"""


class ChiefContentOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def pitch_concept_to_ceo(self, state):
        """Generates a novel concept proposal to submit for CEO approval."""
        print("💡 [CCO Agent] Brainstorming fresh content pitch...")
        history = get_topic_history_summary(state, max_items=10)
        user_prompt = f"Recent channel topics: {json.dumps(history)}. Propose a fresh, viral financial topic concept."

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CCO_PITCH_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                response_format={"type": "json_object"}
            )
            pitch = json.loads(res.choices[0].message.content)
            print(f"  📌 Pitched Topic: '{pitch.get('proposed_topic')}'")
            return pitch
        except Exception as e:
            print(f"⚠️ CCO Pitch warning: {e}")
            return None

    def create_script(self, category, custom_directive=None):
        """Generates the full 60-second script JSON payload."""
        state = load_state()
        recent_topics = get_topic_history_summary(state, max_items=10)
        deliberations = state.get("agent_deliberations", [])[:5]

        print(f"\n📝 [CCO Agent] Writing script for Category: '{category}'")

        user_prompt = f"""
        CATEGORY: {category}
        {"SPECIFIC DIRECTIVE: " + custom_directive if custom_directive else ""}
        RECENTLY USED TOPICS TO AVOID: {json.dumps(recent_topics)}
        AGENT MEMORY & CEO FEEDBACK: {json.dumps(deliberations)}

        Task: Write a new 60-second financial script (~130-150 words) with EXACTLY 20 visual scene prompts.
        """

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CCO_SCRIPT_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            script_payload = json.loads(res.choices[0].message.content)

            # Ensure strict 20 visual prompts count
            visuals = script_payload.get("visual_prompts", [])
            if len(visuals) != 20:
                print(f"⚠️ Prompt count mismatch ({len(visuals)} received). Adjusting to 20...")
                while len(visuals) < 20:
                    visuals.append("Dark ambient cinematic stock video of luxury finance and money")
                script_payload["visual_prompts"] = visuals[:20]

            # Record generated topic into shared state memory
            log_generated_video(state, script_payload.get("topic", "Financial Topic"), category)

            print(f"✅ [CCO Agent] Script completed: '{script_payload.get('title')}'")
            return script_payload

        except Exception as e:
            print(f"❌ Error in CCO script generation: {e}")
            raise e


if __name__ == "__main__":
    cco = ChiefContentOfficer()
    state = load_state()
    cat = get_next_category(state)
    script_output = cco.create_script(category=cat)

    with open("current_script.json", "w", encoding="utf-8") as f:
        json.dump(script_output, f, indent=4)
    print("💾 Script saved to current_script.json!")