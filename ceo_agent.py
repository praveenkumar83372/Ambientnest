"""
Chief Executive Officer (CEO) Agent
Main orchestrator for strategic decisions, performance evaluation, 
YouTube channel analytics, and continuous channel optimization.

Responsibilities:
1. Analyzes live YouTube channel statistics to guide C-Suite strategy.
2. Directs CCO on target video length, high-RPM niches, and trending keywords.
3. Evaluates past video metrics to refine channel memory (channel_state.json).
"""

import os
import json
from groq import Groq
from channel_state import load_state, save_state, get_topic_history_summary

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CEO_SYSTEM_PROMPT = """
You are the Chief Executive Officer (CEO) of a high-growth faceless YouTube Shorts media empire in the Wealth and Finance niche.

YOUR ROLE:
1. Review overall channel performance metrics and previous topic history.
2. Formulate strategic directives for the content team (CCO & Visual Engine).
3. Ensure high Audience Retention, High CTR, and High RPM execution.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "executive_summary": "Brief 1-sentence strategic assessment",
    "target_script_length": 150,
    "focus_niche": "Billionaire Mindsets / Dark Psychology of Wealth",
    "strategic_directive": "Focus on high-stakes hooks mentioning real billionaires (Elon Musk, Warren Buffett) to maximize retention.",
    "recommended_hashtags": "#Shorts #Wealth #Finance #Money #Billionaires"
}
"""


class ChiefExecutiveOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def analyze_channel_data(self, youtube_client, channel_id=None):
        """
        Fetches live channel analytics via YouTube Data API v3 and computes SEO strategy.
        If channel_id is not provided, defaults to checking authenticated user's channel ('mine=True').
        """
        print("\n👔 [CEO Agent] Analyzing Live YouTube Channel Statistics & Performance...")
        try:
            if channel_id:
                request = youtube_client.channels().list(
                    part="statistics,snippet",
                    id=channel_id
                )
            else:
                request = youtube_client.channels().list(
                    part="statistics,snippet",
                    mine=True
                )

            response = request.execute()

            if not response.get('items'):
                print("⚠️ [CEO Agent] No channel found with provided parameters. Using default growth targets.")
                return self._get_fallback_seo_strategy()

            stats = response['items'][0]['statistics']
            snippet = response['items'][0]['snippet']

            channel_title = snippet.get('title', 'Wealth Shorts Channel')
            views = int(stats.get('viewCount', 0))
            subscribers = int(stats.get('subscriberCount', 0))
            video_count = int(stats.get('videoCount', 0))

            print(f"📊 [CEO REPORT] Channel: '{channel_title}'")
            print(f"   📈 Views: {views:,} | 👥 Subscribers: {subscribers:,} | 🎬 Videos: {video_count}")

            # Dynamic strategy adaptation based on channel size
            target_words = 145 if video_count > 5 else 135  # Dynamic word length targeting ~50-58s
            
            seo_strategy = {
                "channel_title": channel_title,
                "total_views": views,
                "subscribers": subscribers,
                "video_count": video_count,
                "target_length_seconds": 55,
                "target_word_count": target_words,
                "voice_id": "en-US-ChristopherNeural",
                "primary_keywords": ["wealth secrets", "passive income 2026", "money mindset", "billionaire habits"],
                "hashtags": "#Shorts #Wealth #Finance #Money #Business #Success"
            }

            # Update shared state with CEO observations
            state = load_state()
            state["latest_channel_stats"] = {
                "views": views,
                "subscribers": subscribers,
                "video_count": video_count
            }
            save_state(state)

            return seo_strategy

        except Exception as e:
            print(f"⚠️ [CEO Agent] YouTube Analytics warning: {e}. Defaulting to baseline strategy.")
            return self._get_fallback_seo_strategy()

    def generate_executive_directive(self, state=None):
        """Generates AI executive directive using Groq Llama-3.3-70B."""
        if not state:
            state = load_state()

        history = get_topic_history_summary(state, max_items=10)
        user_prompt = f"Channel state history: {json.dumps(history)}. Formulate executive directives for today's video production."

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CEO_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            directive = json.loads(res.choices[0].message.content)
            print(f"👔 [CEO DIRECTIVE]: {directive.get('executive_summary')}")
            return directive
        except Exception as e:
            print(f"⚠️ CEO Directive error: {e}")
            return {
                "executive_summary": "Maintain high retention and fast-paced hook.",
                "target_script_length": 145,
                "focus_niche": "Wealth & Financial Psychology",
                "strategic_directive": "Hook viewers within first 3 seconds with billionaire money facts.",
                "recommended_hashtags": "#Shorts #Wealth #Finance #Money"
            }

    def _get_fallback_seo_strategy(self):
        """Fallback SEO parameters if API data is inaccessible."""
        return {
            "channel_title": "Ambientnest Wealth",
            "total_views": 0,
            "subscribers": 0,
            "video_count": 0,
            "target_length_seconds": 55,
            "target_word_count": 145,
            "voice_id": "en-US-ChristopherNeural",
            "primary_keywords": ["wealth secrets", "passive income 2026", "money mindset"],
            "hashtags": "#Shorts #Wealth #Finance #Money #Business"
        }


if __name__ == "__main__":
    ceo = ChiefExecutiveOfficer()
    state = load_state()
    directive = ceo.generate_executive_directive(state)
    print("\n💾 Generated CEO Directive:\n", json.dumps(directive, indent=4))