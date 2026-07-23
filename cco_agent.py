"""
Chief Content Officer (CCO) Agent
Generates high-retention, high-research 60-second viral scripts for YouTube Shorts.
Features dynamic morning/evening news hooks and category rotation.
"""

import os
import json
from datetime import datetime, timezone
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
   - URGENT HOOK: The opening 3 seconds MUST leverage current breaking business news context matching the target time of day.
   - VARIETY REQUIREMENT: Do NOT focus exclusively on Bitcoin unless assigned to the Crypto category. Incorporate banking secrets, billionaire moves (Warren Buffett, BlackRock), inflation, taxes, or market trends.
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
   - Provide 20 specific visual scene descriptions (1 prompt every 3s).

STRICT JSON OUTPUT FORMAT ONLY:
{
    "topic": "Specific Researched Topic",
    "category": "Assigned Strategy Category",
    "title": "🧠 How Banks Mind-Trick You Into Debt 💸 #Shorts #Ambientnest",
    "description": "Exposing the dark banking tactics used to keep the middle class trapped in endless interest cycles. In this episode of Ambientnest Wealth, we break down how central banks and lending algorithms capitalize on consumer debt. Discover the exact wealth-preservation strategy top 1% investors use to leverage debt into tax-free cash flow.\n\nSubscribe to @Ambientnest for daily deep-dive financial intelligence!\n\n#Ambientnest #WealthSecrets #FinanceTips #MoneyMindset #Billionaires #Shorts #Investing",
    "tags": ["ambientnest", "ambientnest wealth", "ambientnest shorts", "finance", "money", "wealth secrets", "banking secrets", "inflation", "passive income", "elon musk", "warren buffett", "rich vs poor", "financial freedom", "investing", "crypto", "dark psychology", "stock market", "economics", "wealth mindset", "shorts"],
    "narration": "Full 140 to 160 word continuous voiceover narration starting with an urgent time-aware news hook...",
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic close up of glowing vault door opening with dark aesthetic lighting",
        ... exactly 20 items ...
    ]
}
"""


class ChiefContentOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def _get_time_aware_greeting(self):
        """Determines whether current run is morning or evening to format news hook appropriately."""
        current_hour = datetime.now(timezone.utc).hour
        if 0 <= current_hour < 12:
            return "THIS MORNING's market headlines", "Just hours ago as markets opened..."
        else:
            return "TONIGHT's closing market update", "As markets close tonight..."

    def create_script(self, category=None, custom_directive=None):
        """Generates full 60s script with dynamic time-of-day hooks and strictly enforced category rotation."""
        state = load_state()
        recent_topics = get_topic_history_summary(state, max_items=10)
        
        # Enforce category rotation if category not explicitly passed
        if not category or category == "None":
            category = get_next_category(state)

        news_context_label, hook_prefix_example = self._get_time_aware_greeting()
        morning_news = fetch_morning_financial_news()
        news_bullets = "\n".join([f"- {headline}" for headline in morning_news])

        print(f"\n📝 [CCO Agent] Writing Script for Category: '{category}' ({news_context_label})")

        user_prompt = f"""
        ASSIGNED CATEGORY: {category}
        TIME-OF-DAY CONTEXT: {news_context_label} (Example hook opening: "{hook_prefix_example}")
        {"SPECIFIC DIRECTIVE: " + custom_directive if custom_directive else ""}
        RECENT TOPICS TO AVOID (DO NOT REPEAT BITCOIN IF RECENTLY COVERED): {json.dumps(recent_topics)}

        BREAKING NEWS HEADLINES ({news_context_label}):
        {news_bullets}

        STRICT RULES:
        1. Narration MUST be between 140 and 160 words.
        2. DO NOT write about Bitcoin unless the category explicitly specifies Crypto. Rotate into banking, real estate, central banks, or billionaire habits.
        3. Match the hook phrasing to the time of day ({news_context_label}).
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
            narration_text = script_payload.get("narration", "")
            word_count = len(narration_text.split())
            print(f"📊 [CCO Agent] Script generated with {word_count} words for category '{category}'.")

            # Ensure 20 visual prompts
            visuals = script_payload.get("visual_prompts", [])
            while len(visuals) < 20:
                visuals.append("Cinematic dark aesthetic clip of Ambientnest wealth and finance")
            script_payload["visual_prompts"] = visuals[:20]

            log_generated_video(state, script_payload.get("topic", "Financial Secret"), category)
            print(f"✅ [CCO Agent] Script completed: '{script_payload.get('title')}'")
            return script_payload

        except Exception as e:
            print(f"❌ Error in CCO script generation: {e}")
            raise e