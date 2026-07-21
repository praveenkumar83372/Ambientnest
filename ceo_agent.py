"""
Chief Executive Officer (CEO) Agent
The executive decision-maker of the automated financial YouTube channel.

Responsibilities:
1. Evaluates channel performance reports from the CAO (Chief Analytics Officer).
2. Reviews and approves/rejects content proposals pitched by the CCO.
3. Sets daily channel directives aligned with high RPM and view targets.
4. Manages shared state memory to learn from high-performing topics over time.
"""

import os
import json
from groq import Groq
from channel_state import load_state, save_state, get_topic_history_summary, get_next_category

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CEO_DIRECTIVE_PROMPT = """
You are the CEO of a high-RPM automated YouTube Shorts finance channel. 
Your goal is to build a high-earning passive income channel starting from $0 budget and 0 subscribers.

YOUR MISSION:
Review the channel briefing and determine the primary strategic directive for today's video production.

Select one of the core categories:
1. "Dark Psychology & Wealth Secrets"
2. "Money Breakdown & Visual Case Studies"
3. "The Wealth Rules & Storytelling"

STRICT JSON OUTPUT FORMAT ONLY (NO MARKDOWN OR EXTRA TEXT):
{
    "chosen_category": "Selected category name",
    "strategy_reasoning": "Why this category will yield high watch time and max RPM today based on analytics",
    "target_hook_style": "e.g., High stakes warning / Curiosity loop / Contrarian claim"
}
"""

CEO_EVALUATION_PROMPT = """
You are the CEO evaluating a new topic pitch from your Chief Content Officer (CCO).

Review the proposal against recent channel topic history and performance goals.
Decide whether to APPROVE or REJECT the proposed topic.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "approved": true or false,
    "ceo_feedback": "Short executive reasoning for approval or rejection",
    "adjusted_category": "Assigned category name if approved, or null if rejected"
}
"""


class ChiefExecutiveOfficer:
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")
        self.client = Groq(api_key=GROQ_API_KEY)

    def issue_daily_directive(self, cao_briefing=None):
        """Generates strategic directive for the channel based on analytics memory."""
        print("👔 [CEO Agent] Reviewing CAO analytics briefing & setting strategy...")
        state = load_state()
        history = get_topic_history_summary(state, max_items=10)

        user_prompt = f"""
        CHANNEL TARGET METRICS: {json.dumps(state.get('metrics', {}))}
        RECENT TOPIC HISTORY: {json.dumps(history)}
        ANALYTICS BRIEFING: {json.dumps(cao_briefing if cao_briefing else {})}

        Determine today's content directive to maximize RPM and watch retention.
        """

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CEO_DIRECTIVE_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            directive_payload = json.loads(res.choices[0].message.content)
            print(f"  📌 Strategic Directive: '{directive_payload.get('chosen_category')}'")
            print(f"  💡 Reasoning: {directive_payload.get('strategy_reasoning')}")
            return directive_payload

        except Exception as e:
            print(f"⚠️ CEO Directive Warning ({e}). Defaulting to rotation category.")
            fallback_category = get_next_category(state)
            return {
                "chosen_category": fallback_category,
                "strategy_reasoning": "Fallback rotation due to API delay",
                "target_hook_style": "Curiosity loop"
            }

    def evaluate_cco_pitch(self, proposal, cao_briefing=None):
        """Reviews CCO's pitch and determines whether to greenlight the concept."""
        if not proposal:
            return {"approved": False, "ceo_feedback": "No proposal submitted", "adjusted_category": None}

        print("\n👔 [CEO Agent] Evaluating CCO concept proposal...")
        state = load_state()
        history = get_topic_history_summary(state, max_items=10)

        user_prompt = f"""
        PROPOSED CONCEPT: {json.dumps(proposal)}
        RECENT TOPICS: {json.dumps(history)}
        ANALYTICS BRIEFING: {json.dumps(cao_briefing if cao_briefing else {})}

        Decide if this concept is high-potential and non-repetitive. Approve or Reject.
        """

        try:
            res = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": CEO_EVALUATION_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            decision = json.loads(res.choices[0].message.content)

            # Record deliberation into shared state memory
            deliberation = {
                "timestamp": state.get("last_updated"),
                "proposed_topic": proposal.get("proposed_topic"),
                "approved": decision.get("approved"),
                "ceo_feedback": decision.get("ceo_feedback")
            }
            state.setdefault("agent_deliberations", []).insert(0, deliberation)
            state["agent_deliberations"] = state["agent_deliberations"][:20]  # Keep last 20
            save_state(state)

            if decision.get("approved"):
                print(f"  ✅ Pitch APPROVED! CEO Feedback: {decision.get('ceo_feedback')}")
            else:
                print(f"  ❌ Pitch REJECTED. CEO Feedback: {decision.get('ceo_feedback')}")

            return decision

        except Exception as e:
            print(f"⚠️ CEO Pitch Evaluation Error: {e}")
            return {"approved": False, "ceo_feedback": "Evaluation error fallback", "adjusted_category": None}


if __name__ == "__main__":
    ceo = ChiefExecutiveOfficer()
    directive = ceo.issue_daily_directive()
    print("\nCEO Output Payload:")
    print(json.dumps(directive, indent=2))