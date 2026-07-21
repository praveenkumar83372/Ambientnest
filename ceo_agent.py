"""
Chief Executive Officer (CEO) Agent
Main orchestrator for strategic decisions, performance evaluation, 
YouTube channel analytics, and continuous channel optimization.
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
2. Evaluate pitches from the Chief Content Officer (CCO).
3. Formulate strategic directives for the content team.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "decision": "APPROVED",
    "executive_summary": "Strategic evaluation of the topic concept",
    "executive_directive": "Focus on high-stakes hooks mentioning real billionaires to maximize retention.",
    "category": "Wealth & Financial Psychology"
}
"""


class ChiefExecutiveOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def evaluate_cco_pitch(self, cco_pitch, cao_briefing=None):
        """Evaluates and refines the CCO content pitch using Groq AI."""
        print("👔 [CEO Agent] Evaluating CCO Pitch and issuing directives...")
        
        if not cco_pitch:
            return {
                "decision": "APPROVED",
                "executive_directive": "Focus on high-stakes hooks mentioning real billionaires to maximize retention.",
                "category": "Wealth Secrets"
            }

        user_prompt = f"CCO Pitch: {json.dumps(cco_pitch)}. CAO Briefing: {json.dumps(cao_briefing)}. Evaluate and give strategic directive."

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
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            print(f"⚠️ CEO Pitch evaluation warning: {e}")
            return {
                "decision": "APPROVED",
                "executive_directive": "Hook viewers within first 3 seconds with shocking money truths.",
                "category": cco_pitch.get("target_category", "Wealth & Finance")
            }

    def issue_daily_directive(self, cao_briefing=None):
        """Generates executive daily directives based on CAO channel briefing."""
        print("👔 [CEO Agent] Issuing daily strategic directive...")
        state = load_state()
        history = get_topic_history_summary(state, max_items=10)
        
        user_prompt = f"CAO Briefing: {json.dumps(cao_briefing)}. Recent history: {json.dumps(history)}. Formulate executive daily directive."

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
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            print(f"⚠️ CEO Issue Daily Directive warning: {e}")
            return {
                "decision": "APPROVED",
                "executive_summary": "Focus on high-retention financial psychology hooks.",
                "executive_directive": "Hook viewers in the first 3 seconds with shocking money truths.",
                "category": "Wealth & Financial Psychology"
            }

    def generate_executive_directive(self, state=None):
        """Alias to issue_daily_directive for backward compatibility."""
        return self.issue_daily_directive(state)

    def analyze_channel_data(self, youtube_client, channel_id=None):
        """Fetches live channel analytics via YouTube Data API v3 and computes SEO strategy."""
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
                return self._get_fallback_seo_strategy()

            stats = response['items'][0]['statistics']
            snippet = response['items'][0]['snippet']

            views = int(stats.get('viewCount', 0))
            subscribers = int(stats.get('subscriberCount', 0))
            video_count = int(stats.get('videoCount', 0))

            print(f"📊 [CEO REPORT] Views: {views:,} | Subs: {subscribers:,} | Videos: {video_count}")

            return {
                "channel_title": snippet.get('title', 'Wealth Shorts Channel'),
                "total_views": views,
                "subscribers": subscribers,
                "video_count": video_count,
                "target_length_seconds": 55,
                "target_word_count": 145,
                "voice_id": "en-US-ChristopherNeural",
                "primary_keywords": ["wealth secrets", "passive income 2026", "money mindset"],
                "hashtags": "#Shorts #Wealth #Finance #Money #Business #Success"
            }

        except Exception as e:
            print(f"⚠️ [CEO Agent] YouTube Analytics warning: {e}. Defaulting to baseline strategy.")
            return self._get_fallback_seo_strategy()

    def _get_fallback_seo_strategy(self):
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
    directive = ceo.issue_daily_directive()
    print("\n💾 Generated CEO Directive:\n", json.dumps(directive, indent=4))