from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional
from datetime import datetime, timedelta
from agents.transcriber import transcribe_audio
from agents.analyzer import analyze_meeting
from agents.action_taker import take_actions
import logging

logger = logging.getLogger(__name__)

class MeetingState(TypedDict):
    audio_path: str
    transcript: str
    summary: str
    sentiment: str
    effectiveness_score: int
    effectiveness_reason: str
    risks: List[str]
    action_items: List[dict]
    actions_taken: List[str]
    agent_decisions: List[str]
    error: Optional[str]

def transcriber_node(state: MeetingState) -> dict:
    logger.info("🎤 Agent 1: Transcribing audio...")
    try:
        transcript = transcribe_audio(state["audio_path"])
        return {"transcript": transcript, "error": None}
    except Exception as e:
        return {"transcript": "", "error": str(e)}

def analyzer_node(state: MeetingState) -> dict:
    if state.get("error") or not state.get("transcript"):
        return {"summary": "", "action_items": [], "sentiment": "neutral", "risks": [], "effectiveness_score": 0, "effectiveness_reason": ""}
    logger.info("🧠 Agent 2: Analyzing meeting...")
    result = analyze_meeting(state["transcript"])
    return {
        "summary": result.get("summary", ""),
        "action_items": result.get("action_items", []),
        "sentiment": result.get("sentiment", "neutral"),
        "risks": result.get("risks", []),
        "effectiveness_score": result.get("effectiveness_score", 5),
        "effectiveness_reason": result.get("effectiveness_reason", ""),
    }

def decision_node(state: MeetingState) -> dict:
    """Agent makes smart decisions before taking actions."""
    logger.info("🤔 Agent: Making smart decisions...")
    decisions = []
    action_items = state.get("action_items", [])
    today = datetime.today()

    for item in action_items:
        # Decision 1: Auto-assign deadline if missing
        if not item.get("deadline"):
            days = 3 if item.get("priority") == "high" else 7
            item["deadline"] = (today + timedelta(days=days)).strftime("%Y-%m-%d")
            decisions.append(f"🗓️ Auto-assigned deadline for '{item['assignee']}': {item['deadline']} (no deadline mentioned)")

        # Decision 2: Escalate to high if risk mentioned
        risks = state.get("risks", [])
        task_lower = item.get("task", "").lower()
        if risks and any(r.lower() in task_lower for r in risks):
            item["priority"] = "high"
            decisions.append(f"🔴 Escalated priority for '{item['assignee']}' — task linked to a risk")

        # Decision 3: Flag urgent if deadline within 2 days
        try:
            dl = datetime.strptime(item["deadline"], "%Y-%m-%d")
            if (dl - today).days <= 2:
                item["priority"] = "high"
                decisions.append(f"⚡ Marked HIGH priority for '{item['assignee']}' — deadline in ≤2 days")
        except Exception:
            pass

    # Decision 4: Warn if meeting effectiveness is low
    if state.get("effectiveness_score", 10) <= 4:
        decisions.append("⚠️ Low meeting effectiveness detected — consider a follow-up meeting")

    # Decision 5: Skip calendar if no action items
    if not action_items:
        decisions.append("ℹ️ No action items found — skipping Slack & Calendar")

    return {"action_items": action_items, "agent_decisions": decisions}

def action_node(state: MeetingState) -> dict:
    if state.get("error") or not state.get("action_items"):
        return {"actions_taken": []}
    logger.info("⚡ Agent 3: Taking actions...")
    actions_taken = take_actions(state["action_items"])
    return {"actions_taken": actions_taken}

def should_take_action(state: MeetingState) -> str:
    if state.get("error") or not state.get("transcript"):
        return END
    if not state.get("action_items"):
        return END
    return "action_taker"

def build_graph():
    graph = StateGraph(MeetingState)
    graph.add_node("transcriber", transcriber_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("decision_maker", decision_node)
    graph.add_node("action_taker", action_node)
    graph.set_entry_point("transcriber")
    graph.add_edge("transcriber", "analyzer")
    graph.add_edge("analyzer", "decision_maker")
    graph.add_conditional_edges("decision_maker", should_take_action)
    graph.add_edge("action_taker", END)
    return graph.compile()

meeting_agent = build_graph()
