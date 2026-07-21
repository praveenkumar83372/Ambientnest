"""
Financial Script Generator Engine (CCO Agent)
Generates high-retention 60-second viral scripts using Groq API (llama-3.3-70b-versatile).

Features:
- Connects to shared memory (channel_state.json) so agents learn from past results.
- Includes a CEO Proposal & Approval loop where new content concepts can be pitched.
- Enforces strict 60-second duration (~130-150 words narration).
- Requires EXACTLY 20 distinct visual prompts (1 every 3 seconds).
- Auto-generates high-CTR title, description, and hashtag metadata.
"""

import os
import json
from groq import Groq
from channel_state import load_state, get_next_category, log_generated_video, get_topic_history_summary, save_state

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CCO_SYSTEM_PROMPT = """
You are the Chief Content Officer (CCO) of a high-RPM faceless YouTube Shorts channel focused on Wealth, Money, and Finance.

YOUR MISSION:
Write a fast-paced, psychological, high-retention 60-second video script (~130-150 words spoken narration).

CRITICAL REQUIREMENTS:
1. NARRATION: Must have a huge hook in the first 3 seconds. High stakes, bold claims, or intriguing dark money secrets.
2. VISUAL PROMPTS: You MUST provide EXACTLY 20 visual scene descriptions (1 visual prompt for every 3-second block of the 60s video).
3. ANTI-REPEAT: Avoid topics already in the recent topic history.
4. METADATA: Generate a viral title (<70 characters with #Shorts), a high-conversion description, and 20 SEO-optimized tags.

STRICT JSON OUTPUT FORMAT ONLY (NO MARKDOWN CODEBLOCKS OR COMMENTARY):
{
    "topic": "Core topic name",
    "category": "Chosen strategy category",
    "title": "Shocking Title Here #Shorts",
    "description": "Engaging short description with key takeaways. Subscribe for daily wealth strategies! #Shorts #Finance #Money #Wealth #Investing",
    "tags": ["finance", "money", "wealth", "business", "investing", "dark psychology", "passive income", "shorts"],
    "narration": "Full 60-second continuous voiceover text here...",
    "visual_prompts": [
        "Prompt 1 (0-3s): Cinematic close up of luxury gold bars in dark lighting",
        "Prompt 2 (3-6s): Financial trader looking at glowing stock charts",
        ... exactly 20 items ...
    ]
}
"""

CEO_EVALUATOR_PROMPT = """
You are the CEO of a high-RPM automated YouTube Shorts finance channel.
Your CCO has proposed a novel content topic concept outside or expanding upon standard rotation.

Review the proposed topic against recent channel history and strategy directives.
Decide whether to APPROVE or REJECT the new idea.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "approved": true or false,
    "ceo_feedback": "Short explanation of why it was approved or rejected",
    "adjusted_category": "The category to assign if approved"
}
"""

CEO_PITCH_PROMPT = """
You are the CCO. You want to propose a fresh, trending, out-of-the-box financial topic concept to the CEO.
Based on past top-performing video themes and current financial trends, suggest a high-RPM viral video concept.

STRICT JSON OUTPUT FORMAT ONLY:
{
    "proposed_topic": "Unique concept title",
    "concept_pitch": "Why this will perform well and go viral",
    "target_category": "Category name or new sub-niche"
}
"""


def propose_new_concept(groq_client, state):
    """CCO Agent pitches a fresh, experimental topic concept."""
    history = get_topic_history_summary(state, max_items=10)
    user_prompt = f"Recent topic history: {json.dumps(history)}. Propose a fresh, high-earning financial topic concept for YouTube Shorts."
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CEO_PITCH_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.8,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ Concept pitch error: {e}")
        return None


def ceo_evaluate_proposal(groq_client, proposal, state):
    """CEO Agent evaluates CCO's proposed concept against shared state & memory."""
    history = get_topic_history_summary(state, max_items=10)
    user_prompt = f"""
    PROPOSED CONCEPT: {json.dumps(proposal)}
    RECENT CHANNEL HISTORY: {json.dumps(history)}
    CHANNEL METRICS: {json.dumps(state.get('metrics', {}))}

    Evaluate if this concept will yield high watch time and RPM. Approve or Reject.
    """
    
    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CEO_EVALUATOR_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ CEO evaluation error: {e}")
        return {"approved": False, "ceo_feedback": "Defaulted due to evaluation error", "adjusted_category": None}


def generate_finance_script():
    """Main CCO script generation pipeline with CEO approval loop and shared memory learning."""
    if not GROQ_API_KEY:
        raise ValueError("❌ GROQ_API_KEY is missing! Please set it in your repository secrets.")

    groq_client = Groq(api_key=GROQ_API_KEY)
    state = load_state()
    
    # --- STEP 1: CCO pitches a fresh idea to the CEO ---
    print("\n💡 [CCO Agent] Brainstorming new content concept...")
    proposal = propose_new_concept(groq_client, state)
    
    active_category = None
    custom_directive = None
    
    if proposal:
        print(f"  📌 CCO Pitched: '{proposal.get('proposed_topic')}'")
        print("\n👔 [CEO Agent] Reviewing proposal against shared memory...")
        ceo_decision = ceo_evaluate_proposal(groq_client, proposal, state)
        
        # Log decision into shared agent memory
        state.setdefault("agent_deliberations", []).insert(0, {
            "timestamp": state.get("last_updated"),
            "proposed_topic": proposal.get("proposed_topic"),
            "approved": ceo_decision.get("approved"),
            "ceo_feedback": ceo_decision.get("ceo_feedback")
        })
        state["agent_deliberations"] = state["agent_deliberations"][:20]  # Keep last 20 in memory
        
        if ceo_decision.get("approved"):
            print(f"  ✅ CEO APPROVED! Feedback: {ceo_decision.get('ceo_feedback')}")
            active_category = ceo_decision.get("adjusted_category") or proposal.get("target_category")
            custom_directive = proposal.get("proposed_topic")
        else:
            print(f"  ❌ CEO REJECTED. Feedback: {ceo_decision.get('ceo_feedback')}")
            print("  🔄 Reverting to standard category rotation...")

    # --- STEP 2: Standard Rotation Fallback if Proposal is Rejected/Skipped ---
    if not active_category:
        active_category = get_next_category(state)

    recent_topics = get_topic_history_summary(state, max_items=10)
    deliberation_memory = state.get("agent_deliberations", [])[:5]

    print(f"\n📝 [CCO Agent] Writing script under Category: '{active_category}'")

    user_prompt = f"""
    CATEGORY: {active_category}
    {"SPECIFIC DIRECTIVE: " + custom_directive if custom_directive else ""}
    RECENTLY USED TOPICS TO AVOID: {json.dumps(recent_topics)}
    RECENT CEO FEEDBACK MEMORY: {json.dumps(deliberation_memory)}

    Task: Write a brand new, highly engaging 60-second script. 
    Ensure narration length is 130 to 150 words and output EXACTLY 20 visual prompts for 3-second scene matching.
    """

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CCO_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        script_payload = json.loads(response.choices[0].message.content)

        # Validate exactly 20 visual prompts
        visual_prompts = script_payload.get("visual_prompts", [])
        if len(visual_prompts) != 20:
            print(f"⚠️ Prompt count mismatch! Got {len(visual_prompts)} prompts. Adjusting/Padding to 20...")
            while len(visual_prompts) < 20:
                visual_prompts.append("Luxury gold and dark ambient financial aesthetic stock video")
            script_payload["visual_prompts"] = visual_prompts[:20]

        # Save to state (shared memory)
        log_generated_video(state, script_payload.get("topic", "Financial Topic"), active_category)

        print(f"✅ Script Generated & Approved: '{script_payload.get('title')}'")
        return script_payload

    except Exception as e:
        print(f"❌ Error during script generation: {e}")
        raise e


if __name__ == "__main__":
    script_data = generate_finance_script()
    with open("current_script.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=4)
    print("💾 Script successfully saved to current_script.json!")