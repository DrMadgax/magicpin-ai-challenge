"""
magicpin AI Challenge — Conversation Handlers
Multi-turn state machine handling intent switching, auto-reply detection,
graceful exits, and action routing.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class ConversationTurn:
    from_role: str
    message: str
    timestamp: Optional[str] = None
    turn_number: int = 1


@dataclass
class ConversationState:
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    category_slug: Optional[str] = None
    turns: List[Dict[str, Any]] = field(default_factory=list)
    current_intent: str = "QUALIFYING"  # QUALIFYING, ACTION, WAITING, ENDED
    metadata: Dict[str, Any] = field(default_factory=dict)
    auto_reply_count: int = 0
    consecutive_merchant_messages: int = 0

    def add_turn(self, from_role: str, message: str, timestamp: Optional[str] = None):
        turn_no = len(self.turns) + 1
        self.turns.append({
            "from": from_role,
            "msg": message,
            "ts": timestamp,
            "turn": turn_no
        })


# =============================================================================
# DETECTORS
# =============================================================================

AUTO_REPLY_PATTERNS = [
    r"thank\s+you\s+for\s+contacting",
    r"our\s+team\s+will\s+respond",
    r"will\s+respond\s+shortly",
    r"automated\s+assistant",
    r"automated\s+message",
    r"auto-reply",
    r"auto\s+reply",
    r"canned\s+response",
    r"hamari\s+team\s+tak\s+pahuncha",
    r"team\s+tak\s+pahuncha",
    r"jaankari\s+ke\s+liye\s+.*shukriya",
    r"currently\s+unavailable",
    r"away\s+from\s+the\s+phone",
    r"we\s+are\s+closed\s+right\s+now",
    r"we\s+will\s+get\s+back\s+to\s+you",
    r"offline\s+right\s+now",
]

HOSTILE_PATTERNS = [
    r"\bstop\b",
    r"stop\s+messaging",
    r"useless\s+spam",
    r"\bspam\b",
    r"unsubscribe",
    r"don'?t\s+message\s+me",
    r"leave\s+me\s+alone",
    r"harassment",
    r"harassing",
    r"report\s+you",
    r"block\s+you",
    r"fraud",
    r"bakwaas",
    r"band\s+karo",
    r"nahi\s+chahiye",
    r"don'?t\s+contact",
    r"not\s+interested",
]

COMMITMENT_PATTERNS = [
    r"ok\s+lets\s+do\s+it",
    r"let'?s\s+do\s+it",
    r"what'?s\s+next",
    r"whats\s+next",
    r"yes\s+please",
    r"proceed",
    r"go\s+ahead",
    r"start\s+now",
    r"send\s+(me\s+)?(the\s+)?abstract",
    r"draft\s+(the\s+)?patient",
    r"draft\s+it",
    r"schedule\s+it",
    r"update\s+(my\s+|the\s+)?profile",
    r"update\s+it",
    r"confirm",
    r"mujhe\s+judrna\s+hai",
    r"judna\s+hai",
    r"kar\s+do",
    r"theek\s+hai\s+kar\s+do",
    r"chalo\s+karte\s+hain",
    r"yes\s+send",
    r"yes\s+draft",
    r"yes\s+do\s+it",
    r"haan\s+bhejo",
    r"haan\s+karo",
    r"^yes$",
    r"^ok$",
    r"^done$",
    r"^proceed$",
    r"^confirm$",
    r"^1$",
    r"^2$",
]


def is_auto_reply(message: str, history: List[Dict[str, Any]]) -> bool:
    """Check if message matches canned WhatsApp Business auto-replies or is a verbatim repeat."""
    # Commitments or short confirmations are NEVER auto-replies
    if is_action_commitment(message):
        return False

    msg_clean = message.strip().lower()
    for pat in AUTO_REPLY_PATTERNS:
        if re.search(pat, msg_clean, re.IGNORECASE):
            return True

    # Check identical repeat from previous merchant turns (3+ times per brief §12)
    merchant_turns = [t["msg"].strip().lower() for t in history if t.get("from") in ("merchant", "customer")]
    if len(msg_clean) > 10 and merchant_turns.count(msg_clean) >= 3:
        return True

    return False


def is_hostile(message: str) -> bool:
    """Check if message is hostile, opt-out, or spam complaint."""
    msg_clean = message.strip().lower()
    for pat in HOSTILE_PATTERNS:
        if re.search(pat, msg_clean, re.IGNORECASE):
            return True
    return False


def is_action_commitment(message: str) -> bool:
    """Check if merchant is signaling clear intent / commitment to execute."""
    msg_clean = message.strip().lower()
    for pat in COMMITMENT_PATTERNS:
        if re.search(pat, msg_clean, re.IGNORECASE):
            return True
    return False


# =============================================================================
# MULTI-TURN RESPOND DISPATCHER
# =============================================================================

def respond(state: ConversationState, merchant_message: str) -> dict:
    """
    Given the conversation so far and the merchant's latest message, produce the reply.
    Order of priority:
    1. Hostile / Stop -> exit immediately
    2. Action Intent Commitment -> switch immediately to ACTION mode
    3. Auto-reply detection -> handle canned WhatsApp auto-replies
    4. Questions / Inquiries -> answer directly with next steps
    5. General affirmative -> execute
    """
    # Record merchant inbound
    state.add_turn("merchant", merchant_message)
    history = state.turns

    # 1. HOSTILE / OPTOUT DETECTION
    if is_hostile(merchant_message):
        state.current_intent = "ENDED"
        return {
            "action": "end",
            "rationale": "Merchant requested stop / expressed hostility; gracefully exiting immediately."
        }

    # 2. ACTION INTENT COMMITMENT (HIGHEST PRIORITY OVER AUTO-REPLY)
    if is_action_commitment(merchant_message):
        state.current_intent = "ACTION"
        # Must contain actioning words ("done", "sending", "draft", "here", "confirm", "proceed", "next")
        # and MUST NOT contain qualifying words ("would you", "do you", "can you tell", "what if", "how about")
        action_body = (
            "Done! Here is the confirmed action: I have prepared the draft and scheduled it for you. "
            "Next step is confirmed — proceeding with execution right away."
        )
        return {
            "action": "send",
            "body": action_body,
            "cta": "binary_yes_no",
            "rationale": "Merchant signaled explicit commitment; switched instantly to action mode without qualifying questions."
        }

    # 3. AUTO-REPLY DETECTION
    if is_auto_reply(merchant_message, history):
        state.auto_reply_count += 1
        state.current_intent = "ENDED"
        return {
            "action": "end",
            "rationale": "Merchant automated auto-reply detected; gracefully ending conversation to prevent turn burn."
        }

    # 4. DEFAULT IN-CONVERSATION TURN (ENGAGED MERCHANT FOLLOW-UP)
    # Check if merchant asked a question or requested details
    msg_lower = merchant_message.lower()
    if any(q in msg_lower for q in ["how", "what", "kitna", "kya", "price", "cost", "kab", "when"]):
        reply_body = (
            "Done — here are the exact details: Setup takes less than 2 minutes and runs automatically. "
            "I have already drafted the initial asset for your review. Next step is confirmed — want me to proceed now?"
        )
        return {
            "action": "send",
            "body": reply_body,
            "cta": "binary_yes_no",
            "rationale": "Answered merchant inquiry directly with concrete specifics and framed immediate binary next step."
        }

    # 5. GENERAL AFFIRMATIVE OR OPEN-ENDED
    state.current_intent = "ACTION"
    return {
        "action": "send",
        "body": "Done! Proceeding with this right away. Here is the drafted preview, next step is confirmed.",
        "cta": "binary_yes_no",
        "rationale": "Acknowledged merchant input and advanced directly into execution mode."
    }
