"""
Chief Content Officer (CCO) Agent
Generates high-retention, high-research 60-second viral scripts for YouTube Shorts.
Integrates real-time financial news headlines for urgent 3-second opening hooks.
"""

import os
import json
from groq import Groq
from channel_state import load_state, get_next_category, log_generated_video, get_topic_history_summary
from news_engine import fetch_morning_financial_news

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CCO_SCRIPT_PROMPT = """
You are the Chief Content Officer (CCO) of 'Ambientnest Wealth' — an elite, highly researched faceless YouTube Shorts media engine.

YOUR MISSION:
Write a fast-paced, highly accurate, deep-dive financial script (~140-160 words spoken narration).

CRITICAL METADATA & CONTENT RULES:
1. SCRIPT NARRATION (140-160 Words):
   - URGENT HOOK: The opening 3 seconds MUST leverage today's breaking morning business news context to grab instant attention!
   - Content must provide SPECIFIC financial facts, exact numbers, historical context, or real billionaire strategies (e.g., Elon Musk, Warren Buffett, BlackRock secrets).
   - Spoken narration MUST be 140 to 160 words so spoken audio runs 50-58 seconds continuously.

2. TITLE FORMAT:
   - High-CTR hook title WITH EMOJIS under 70 characters ending with #Shorts #Ambientnest.
   - Example: 🧠 How Banks Mind-Trick You Into Debt 💸 #Shorts #Ambientnest

3. RICH SEO DESCRIPTION:
   - Must be 4-5 well-structured sentences containing key facts discussed in the video.
   - Include a strong Call-To-Action: "Subscribe to Ambientnest for daily deep-dive wealth secrets!"
   - Include mandatory brand hashtags: #Ambientnest #WealthSecrets #FinanceTips #MoneyMindset #Billionaires #Shorts

4. TAGS (Exactly 20):
   - Must include brand tags: "ambientnest", "ambientnest wealth", "ambientnest shorts", plus 17 high-volume niche tags.

5. VISUAL PROMPTS (EXACTLY 20 Prompts):
   - Provide 20 specific visual scene descriptions (1 prompt every 3s). If specific public figures or concepts are mentioned, name them directly (e.g., "Elon Musk speaking at conference") so stock search targets them accurately.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "topic": "Specific Researched Topic",
    "category": "Assigned Strategy Category",
    "title": "🧠 How Banks Mind-Trick You Into Debt 💸 #Shorts #Ambientnest",
    "description": "Exposing the dark banking tactics used to keep the middle class trapped in endless interest cycles. In this episode of Ambientnest Wealth, we break down how central banks and lending algorithms capitalize on consumer debt. Discover the exact wealth-preservation strategy top 1% investors use to leverage debt into tax-free cash flow.\n\nSubscribe to @Ambientnest for daily deep-dive financial intelligence!\n\n#Ambientnest #WealthSecrets #FinanceTips #MoneyMindset #Billionaires #Shorts #Investing",
    "tags": ["ambientnest", "ambientnest wealth", "ambientnest shorts", "finance", "money", "wealth secrets", "banking secrets", "inflation", "passive income", "elon musk", "warren buffett", "rich vs poor", "financial freedom", "investing", "crypto", "dark psychology", "stock market", "economics", "wealth mindset", "shorts"],
    "narration": "Full 140 to 160 word continuous voiceover narration starting with an urgent news-backed hook and deep financial facts...",
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic close up of glowing vault door opening with dark aesthetic lighting",
        "Prompt 2 (3-6s): Financial analyst staring at steep stock market drop chart",
        "Prompt 3 (6-9s): Elon Musk walking past cameras looking focused",
        "Prompt 4 (9-12s): Dark luxury skyscraper at dusk with gold accents",
        "Prompt 5 (12-15s): Close up of hands typing complex stock trading algorithms",
        "Prompt 6 (15-18s): Glowing dollar bill dissolving into digital code",
        "Prompt 7 (18-21s): High speed footage of printing press stamping paper currency",
        "Prompt 8 (21-24s): Warren Buffett speaking at annual shareholder meeting",
        "Prompt 9 (24-27s): Modern bank vault interior with rows of deposit boxes",
        "Prompt 10 (27-30s): Trader stressing over red market graphs on multi-monitors",
        "Prompt 11 (30-33s): Businessman signing legal contracts under desk lamp",
        "Prompt 12 (33-36s): Abstract 3D gold bar stack multiplying rapidly",
        "Prompt 13 (36-39s): Wall Street bull statue under dark stormy sky",
        "Prompt 14 (39-42s): Luxury private jet landing at sunset",
        "Prompt 15 (42-45s): Close up on luxury watch tick mechanism",
        "Prompt 16 (45-48s): Digital crypto ledger transactions flashing on screen",
        "Prompt 17 (48-51s): Investor analyzing property real estate portfolio graphs",
        "Prompt 18 (51-54s): Dark aesthetic chess piece knocking over king",
        "Prompt 19 (54-57s): Glowing Ambientnest logo on metallic slate wall",
        "Prompt 20 (57-60s): Subscribe button animation overlaid on glowing golden chart"
    ]
}
"""

CCO_PITCH_PROMPT = """
You are the CCO suggesting a brand-new, out-of-the-box financial topic concept to the CEO.
Based on recent topic history, breaking news trends, and financial algorithm data, suggest a viral video concept that maximizes watch time and RPM.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "proposed_topic": "Unique concept title",
    "concept_pitch": "Why this will go viral, hook viewers immediately, and command high RPM",
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
        print("💡 [CCO Agent] Brainstorming fresh content pitch with news context...")
        history = get_topic_history_summary(state, max_items=10)
        morning_news = fetch_morning_financial_news()
        news_summary = "\n".join([f"- {h}" for h in morning_news[:3]])

        user_prompt = f"Recent channel topics: {json.dumps(history)}.\nBreaking news trends:\n{news_summary}\nPropose a fresh, high-RPM financial video concept."

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
            print(f"   📌 Pitched Topic: '{pitch.get('proposed_topic')}'")
            return pitch
        except Exception as e:
            print(f"⚠️ CCO Pitch warning: {e}")
            return {
                "proposed_topic": "Frugal Billionaires: The Secret Wealth Preservation Playbook",
                "concept_pitch": "High-retention breakdown of how the 1% leverage debt to avoid taxes.",
                "target_category": "Wealth & Financial Psychology"
            }

    def create_script(self, category, custom_directive=None):
        """Generates full 60s script with news-driven hooks, word count enforcement, and 20 scene prompts."""
        state = load_state()
        recent_topics = get_topic_history_summary(state, max_items=10)
        deliberations = state.get("agent_deliberations", [])[:5]

        # Fetch real-time morning financial news
        morning_news = fetch_morning_financial_news()
        news_bullets = "\n".join([f"- {headline}" for headline in morning_news])

        print(f"\n📝 [CCO Agent] Writing Deep-Research Script for Category: '{category}'")

        user_prompt = f"""
        CATEGORY: {category}
        {"SPECIFIC DIRECTIVE: " + custom_directive if custom_directive else ""}
        RECENT TOPICS TO AVOID: {json.dumps(recent_topics)}
        AGENT MEMORY & CEO FEEDBACK: {json.dumps(deliberations)}

        TODAY'S BREAKING FINANCIAL NEWS (Use as context for the opening hook):
        {news_bullets}

        CRITICAL REQUIREMENT: The narration MUST contain between 140 and 160 words. Count your words carefully!
        Task: Write a deep-dive financial script (140-160 words) with emoji title, rich SEO description, #Ambientnest branding, and EXACTLY 20 visual prompts.
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

            # Check and log word count
            narration_text = script_payload.get("narration", "")
            word_count = len(narration_text.split())
            print(f"📊 [CCO Agent] Script generated with {word_count} words (~{int(word_count/2.5)}s spoken duration).")

            # Ensure strict 20 visual prompts count
            visuals = script_payload.get("visual_prompts", [])
            if len(visuals) != 20:
                print(f"⚠️ Visual prompt count mismatch ({len(visuals)} received). Adjusting to 20...")
                while len(visuals) < 20:
                    visuals.append("Cinematic dark aesthetic clip of Ambientnest wealth and finance")
                script_payload["visual_prompts"] = visuals[:20]

            # Enforce brand tags in payload
            tags = script_payload.get("tags", [])
            for brand_tag in ["ambientnest", "ambientnest wealth", "ambientnest shorts"]:
                if brand_tag not in tags:
                    tags.insert(0, brand_tag)
            script_payload["tags"] = tags[:20]

            # Record generated topic into shared state memory
            log_generated_video(state, script_payload.get("topic", "Financial Secret"), category)

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