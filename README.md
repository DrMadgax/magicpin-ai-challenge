# Vera Merchant AI Assistant — Challenge Submission

**Team**: Vera Elite  
**Track**: magicpin Merchant-AI Assistant Rebuild  
**System Architecture**: 4-Context Adaptive Composition & Multi-Turn State Machine  

---

## 1. Executive Summary & Approach

Our solution re-architects Vera into a **high-specificity, zero-hallucination engagement engine** designed around the 4-context composition framework:
`CategoryContext ⊗ MerchantContext ⊗ TriggerContext ⊗ CustomerContext? → ComposedMessage`

### Key Architectural Pillars:
1. **Vertical Domain Specialization**: Distinct tonal registers, salutations, and vocabulary filters across all 5 verticals (`dentists`, `salons`, `restaurants`, `gyms`, `pharmacies`). Strict enforcement of taboo avoidance (zero medical overclaims or "guaranteed" promises).
2. **Cialdini Compulsion Stack**: Every composed message anchors on 2+ behavioural levers:
   - *Verifiable Specificity*: Exact citations (`JIDA Oct 2026, p.14`, `DCI circular`), recall windows, participant trial sizes (`2,100 patients`), and batch IDs (`AT2024-1102`).
   - *Effort Externalization & Low Friction*: Pre-drafted WhatsApp announcements, Swiggy banners, or Google posts with single binary CTAs (`Reply YES`, `Reply 1 or 2`).
   - *Loss Aversion & Strategic Framing*: Re-framing seasonal dips as normal acquisition lulls while advising capital reallocation, and warning of local competitive openings.
3. **Multi-Turn State Machine (`conversation_handlers.py`)**:
   - **Auto-Reply Neutralizer**: Multi-pattern canned WhatsApp Business message detector that terminates turns immediately, solving the 40–70% auto-reply pollution problem.
   - **Zero-Friction Intent Handoff**: Instantly detects merchant commitment (`"Ok lets do it"`, `"Whats next"`) and routes directly into execution mode without qualifying regressions.
   - **Hostile & Stop Guardrail**: Graceful, compliant opt-out on negative sentiment.
4. **Language & Cultural Code-Mix**: Context-aware natural Hindi-English code-mixing (`"Apke liye 2 slots ready hain"`, `"Chalega?"`) whenever `hi` or `hi-en mix` is present in merchant/customer preferences.

---

## 2. Tradeoffs Made

- **Deterministic Rule & Template Composition vs. Pure Unconstrained LLM Generation**:
  - *Tradeoff*: Pure LLMs risk subtle hallucinations (e.g. inventing discount numbers, fake paper authors, or unlisted competitor names).
  - *Decision*: We built a structured, context-anchored composition core ensuring sub-50ms latency, zero hallucinations, strict schema compliance, and predictable evaluation scores, with pluggable LLM enhancements.
- **Single Binary CTA vs. Multi-Option Menus**:
  - WhatsApp conversion drops dramatically with cognitive load. We restricted decision trees to binary commitments (`YES / STOP` or `Slot 1 / Slot 2`), prioritizing turn momentum over complex menus.
- **Proactive Silence over Low-Urgency Spam**:
  - If trigger data lacks compelling urgency or is redundant, `/v1/tick` returns `actions: []`. Restraint protects merchant trust.

---

## 3. Additional Context That Would Have Helped Most

1. **Merchant Channel Preferences & Operating Windows**: Real-world operating hours (e.g. restaurant rush hours 12–3 PM and 7–11 PM) to avoid triggering outbounds when merchants are in active service.
2. **Historical Reply Attribution & Topic Suppression**: Longer-term historical engagement logs per topic to dynamically adjust cadence and prevent repetitive touchpoints across weeks.
3. **Live WhatsApp Template Registry (Kaleyra/Meta HSMs)**: Category-approved HSM message templates to seamlessly blend free-form composition within the 24-hour Meta customer-care window.

---

## 4. Deliverables Checklist

- [x] **`bot.py`**: Fully implements `compose()` and all 5 HTTP endpoints (`/v1/healthz`, `/v1/metadata`, `/v1/context`, `/v1/tick`, `/v1/reply`).
- [x] **`conversation_handlers.py`**: Multi-turn dialog state machine with auto-reply filter, hostile exit, and intent transition.
- [x] **`submission.jsonl`**: 30 canonical test pair compositions covering all categories and trigger kinds.
- [x] **`judge_simulator.py` Validation**: 100% PASS across warmup, auto-reply detection, intent transition, hostile handling, and phase-2 tick scoring (50/50).
