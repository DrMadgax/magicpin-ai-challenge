"""
magicpin AI Challenge — Vera Merchant Assistant Bot
Exposes the 5 HTTP testing endpoints and implements compose() per the competition specification.
"""

from __future__ import annotations
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from composer import compose as compose_impl
from conversation_handlers import ConversationState, respond

START_TIME = time.time()
app = FastAPI(title="Vera Merchant Assistant Bot", version="2.0.0")

# In-memory context and conversation stores
# key: (scope, context_id) -> {"version": int, "payload": dict}
contexts: Dict[tuple[str, str], Dict[str, Any]] = {}

# key: conversation_id -> ConversationState
conversations: Dict[str, ConversationState] = {}


# =============================================================================
# CORE COMPOSITION API (§7.1)
# =============================================================================

def compose(category: dict, merchant: dict, trigger: dict, customer: dict | None = None) -> dict:
    """
    Inputs are the dicts loaded from the dataset JSON.
    Return a dict with keys: body, cta, send_as, suppression_key, rationale.
    Deterministic, <30s execution time, 0-hallucination.
    """
    return compose_impl(category, merchant, trigger, customer)


# =============================================================================
# PYDANTIC SCHEMAS (§2 & §3)
# =============================================================================

class ContextPayload(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: Optional[str] = None


class TickRequest(BaseModel):
    now: Optional[str] = None
    available_triggers: List[str] = Field(default_factory=list)


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: Optional[str] = None
    customer_id: Optional[str] = None
    from_role: str = "merchant"
    message: str
    received_at: Optional[str] = None
    turn_number: int = 1


@app.get("/")
async def root():
    return {
        "bot": "Vera Merchant Assistant Bot",
        "status": "online",
        "documentation": "/docs",
        "health": "/v1/healthz",
        "metadata": "/v1/metadata"
    }


# =============================================================================
# ENDPOINT 1: GET /v1/healthz (§2.4)
# =============================================================================

@app.get("/v1/healthz")
async def healthz():
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
    for (scope, _), _ in contexts.items():
        if scope in counts:
            counts[scope] += 1
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
        "contexts_loaded": counts
    }


# =============================================================================
# ENDPOINT 2: GET /v1/metadata (§2.5)
# =============================================================================

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": "Vera Elite",
        "team_members": ["Antigravity Engineer"],
        "model": "hybrid-deterministic-llm",
        "approach": "4-context structured composer with multi-lever compulsion engine, Cialdini heuristics, and multi-turn state machine",
        "contact_email": "vera-team@magicpin.in",
        "version": "2.0.0",
        "submitted_at": "2026-04-26T10:00:00Z"
    }


# =============================================================================
# ENDPOINT 3: POST /v1/context (§2.1)
# =============================================================================

@app.post("/v1/context")
async def push_context(body: ContextPayload):
    key = (body.scope, body.context_id)
    cur = contexts.get(key)
    
    # Idempotent check: if incoming version is strictly older than stored, return 409
    if cur and cur["version"] > body.version:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "accepted": False,
                "reason": "stale_version",
                "current_version": cur["version"]
            }
        )
    
    # Store atomically
    contexts[key] = {
        "version": body.version,
        "payload": body.payload
    }
    
    return {
        "accepted": True,
        "ack_id": f"ack_{body.context_id}_v{body.version}",
        "stored_at": datetime.now(timezone.utc).isoformat()
    }


# =============================================================================
# ENDPOINT 4: POST /v1/tick (§2.2)
# =============================================================================

@app.post("/v1/tick")
async def tick(body: TickRequest):
    actions = []
    
    for trg_id in body.available_triggers:
        trg_ctx = contexts.get(("trigger", trg_id), {}).get("payload")
        if not trg_ctx:
            continue
        
        merchant_id = trg_ctx.get("merchant_id")
        customer_id = trg_ctx.get("customer_id")
        
        merchant_ctx = contexts.get(("merchant", merchant_id), {}).get("payload")
        if not merchant_ctx:
            continue
            
        category_slug = merchant_ctx.get("category_slug", "")
        category_ctx = contexts.get(("category", category_slug), {}).get("payload", {})
        
        customer_ctx = None
        if customer_id:
            customer_ctx = contexts.get(("customer", customer_id), {}).get("payload")
            
        composed = compose(category_ctx, merchant_ctx, trg_ctx, customer_ctx)
        
        # Build action object
        conv_id = f"conv_{merchant_id}_{trg_id}"
        actions.append({
            "conversation_id": conv_id,
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "send_as": composed["send_as"],
            "trigger_id": trg_id,
            "template_name": f"vera_{trg_ctx.get('kind', 'generic')}_v1",
            "template_params": [
                merchant_ctx.get("identity", {}).get("name", ""),
                composed["body"][:60],
                composed["cta"]
            ],
            "body": composed["body"],
            "cta": composed["cta"],
            "suppression_key": composed["suppression_key"],
            "rationale": composed["rationale"]
        })
        
    return {"actions": actions}


# =============================================================================
# ENDPOINT 5: POST /v1/reply (§2.3)
# =============================================================================

@app.post("/v1/reply")
async def reply(body: ReplyRequest):
    # Retrieve or initialize state (reset on turn <= 2 for idempotent test runs)
    conv_id = body.conversation_id
    if conv_id not in conversations or body.turn_number <= 2:
        conversations[conv_id] = ConversationState(
            conversation_id=conv_id,
            merchant_id=body.merchant_id,
            customer_id=body.customer_id
        )
    
    state = conversations[conv_id]
    result = respond(state, body.message)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bot:app", host="0.0.0.0", port=8080, reload=False)
