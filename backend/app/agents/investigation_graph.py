"""LangGraph Multi-Agent State Graph for Root Cause & Operational Investigation.

Implements the Responsible AI guardrail enforcing strict Evidence vs. Hypothesis separation
with multi-agent reflection and Human-in-the-Loop checkpoints.
Equipped with live OpenAI GPT-4o-mini integration across all agent nodes with deterministic fallback.
"""

import json
from typing import TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.prompts import (
    INVESTIGATION_SYSTEM_PROMPT,
    INVESTIGATION_REFLECTION_PROMPT,
)

logger = get_logger("cva.agent.investigation_graph")

# Forbidden certainty phrases that trigger compliance rejection
CERTAINTY_PHRASES = [
    "is caused by",
    "the exact root cause is",
    "due to confirmed bug",
    "is definitively due to",
    "has been proven to be",
    "is because the developer",
    "is 100% due to",
]

# Mapping from product/category to canonical generic enterprise team
DOMAIN_TEAM_MAP: Dict[str, str] = {
    "c1_mobile_ios": "digital_eng_mobile",
    "c1_mobile_android": "digital_eng_mobile",
    "venture_x": "travel_lounges_prod",
    "venture": "travel_lounges_prod",
    "savor_one": "travel_lounges_prod",
    "banking_360_checking": "payments_ops",
    "banking_360_savings": "payments_ops",
    "banking_360_cd": "payments_ops",
    "c1_shopping_extension": "shopping_eng",
    "shopping_extension": "shopping_eng",
    "eno_virtual_assistant": "digital_ai_security",
    "creditwise": "digital_ai_security",
    "c1_cafe": "cafe_ops",
    "c1_branch_network": "cafe_ops",
    "branches": "cafe_ops",
}


class InvestigationState(TypedDict, total=False):
    """LangGraph shared state across investigation agent nodes."""
    cluster_id: str
    cluster_title: str
    affected_product_id: str
    category: str
    review_count: int
    negative_pct: float
    representative_quotes: List[str]
    sample_reviews: List[Dict[str, Any]]
    velocity_summary: Optional[Dict[str, Any]]

    # Runtime LLM Configuration
    llm_provider: Optional[str]
    openai_api_key: Optional[str]
    model_name: Optional[str]

    # Agent node outputs
    observed_evidence: str
    investigation_hypothesis: str
    suggested_team_id: str
    recommended_action: str
    confidence: float

    # Compliance & Reflection
    compliance_passed: bool
    reflection_notes: str
    iteration_count: int

    # Human-in-the-Loop
    status: str
    human_feedback: Optional[Dict[str, Any]]


def _get_openai_client(state: InvestigationState) -> Optional[Any]:
    """Helper to obtain an OpenAI client if configured."""
    provider = state.get("llm_provider")
    if not provider or provider.lower() != "openai":
        return None
    api_key = state.get("openai_api_key") or settings.OPENAI_API_KEY
    if not api_key or "mock" in api_key.lower():
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as exc:
        logger.warning(f"Failed to initialize OpenAI client in LangGraph: {exc}")
        return None


def gather_evidence_node(state: InvestigationState) -> Dict[str, Any]:
    """Node 1: Evidence Gatherer Agent. Extracts strictly factual customer symptoms and counts."""
    quotes = state.get("representative_quotes", [])
    quotes_text = "\n".join([f"- \"{q}\"" for q in quotes[:4]]) if quotes else "- No direct customer quotes provided."
    count = state.get("review_count", 0)
    neg_pct = state.get("negative_pct", 0.0)
    product_id = state.get("affected_product_id", "unknown_product")
    title = state.get("cluster_title", "Unknown Cluster")

    evidence = (
        f"Observed Evidence for {title} (Product: {product_id}):\n"
        f"• Total review volume: {count} customer reports ({neg_pct:.1f}% negative sentiment).\n"
        f"• Representative customer statements:\n{quotes_text}"
    )
    return {"observed_evidence": evidence}


def generate_hypotheses_node(state: InvestigationState) -> Dict[str, Any]:
    """Node 2: Hypothesis Generator Agent. Uses GPT-4o-mini (or deterministic fallback) to formulate areas to investigate."""
    client = _get_openai_client(state)
    product_id = state.get("affected_product_id", "")
    title = state.get("cluster_title", "")
    category = state.get("category", "")
    quotes = state.get("representative_quotes", [])
    model = state.get("model_name") or settings.LLM_MODEL or "gpt-4o-mini"

    # --- Live OpenAI GPT-4o-mini Call ---
    if client:
        try:
            prompt = (
                f"Cluster: {title}\n"
                f"Product: {product_id} (Category: {category})\n"
                f"Review Count: {state.get('review_count', 0)} ({state.get('negative_pct', 0)}% negative)\n"
                f"Customer Quotes:\n" + "\n".join([f'- "{q}"' for q in quotes[:4]]) + "\n\n"
                "Formulate a tentative engineering and operational hypothesis explaining potential root causes to investigate. "
                "CRITICAL: Start with 'Hypothesis: Investigate whether...' and do NOT state anything as a confirmed bug or proven fact. "
                "Return JSON: {\"hypothesis\": \"string\"}"
            )
            response = client.chat.completions.create(
                model=model,
                temperature=settings.LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": INVESTIGATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            if "hypothesis" in data and len(data["hypothesis"]) > 10:
                logger.info(f"Generated hypothesis via OpenAI {model} for cluster '{title}'")
                return {"investigation_hypothesis": data["hypothesis"]}
        except Exception as exc:
            logger.warning(f"OpenAI hypothesis generation failed, falling back to deterministic: {exc}")

    # --- Deterministic Fallback Rules (For fast offline tests & zero-key mode) ---
    title_lower = title.lower()
    if "face id" in title_lower or "biometric" in title_lower or "login" in title_lower or "crash" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate potential nil-unwrapping or unhandled exception in the iOS biometric "
            "authentication callback upon app foreground initialization. Verify whether the recent client update "
            "introduced an incompatible keychain access entitlement."
        )
    elif "lounge" in title_lower or "crowd" in title_lower or "travel" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate whether peak flight departure banks are exceeding physical lounge seating capacity. "
            "Evaluate whether digital waitlist throughput is creating bottlenecks at the check-in desk."
        )
    elif "virtual" in title_lower or "eno" in title_lower or "declined" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate whether merchant category code (MCC) validation or card expiration date formatting "
            "in virtual card generation is causing checkout gateway declines."
        )
    elif "shopping" in title_lower or "extension" in title_lower or "freeze" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate potential memory leak or DOM polling loop collision in the browser content script "
            "during coupon auto-injection."
        )
    elif "wi-fi" in title_lower or "wifi" in title_lower or "cafe" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate whether guest captive portal DHCP lease exhaustion or access point firmware "
            "instability is causing connection drops during high foot traffic."
        )
    elif "fee" in title_lower or "overdraft" in title_lower:
        hypothesis = (
            "Hypothesis: Investigate whether customer confusion stems from end-of-day ledger posting sequence order "
            "or delayed pending authorization settlements."
        )
    else:
        hypothesis = (
            f"Hypothesis: Investigate whether upstream service latency or recent configuration changes impacted "
            f"{product_id} workflows in the {category} domain."
        )

    return {"investigation_hypothesis": hypothesis}


def synthesize_action_plan_node(state: InvestigationState) -> Dict[str, Any]:
    """Node 3: Action Plan Synthesizer. Synthesizes 3-step remediation and assigns team via GPT-4o-mini."""
    client = _get_openai_client(state)
    product_id = state.get("affected_product_id", "")
    team_id = DOMAIN_TEAM_MAP.get(product_id, "digital_eng_mobile")
    title = state.get("cluster_title", "")
    category = state.get("category", "")
    hypothesis = state.get("investigation_hypothesis", "")
    model = state.get("model_name") or settings.LLM_MODEL or "gpt-4o-mini"

    # --- Live OpenAI GPT-4o-mini Call ---
    if client:
        try:
            prompt = (
                f"Cluster: {title}\n"
                f"Product: {product_id} (Category: {category})\n"
                f"Suggested Team: {team_id}\n"
                f"Investigation Hypothesis: {hypothesis}\n\n"
                "Synthesize a numbered 3-step actionable engineering and operational remediation playbook. "
                "Also assign the most suitable enterprise team ID from: "
                "[digital_eng_mobile, payments_ops, travel_lounges_prod, cafe_ops, digital_ai_security, shopping_eng, customer_exp] "
                "and an estimated confidence score between 0.80 and 0.98. "
                "Return JSON: {\"recommended_action\": \"1. ...\\n2. ...\\n3. ...\", \"suggested_team_id\": \"...\", \"confidence\": 0.92}"
            )
            response = client.chat.completions.create(
                model=model,
                temperature=settings.LLM_TEMPERATURE,
                messages=[
                    {"role": "system", "content": INVESTIGATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=400,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            if "recommended_action" in data and len(data["recommended_action"]) > 10:
                logger.info(f"Synthesized action plan via OpenAI {model} for cluster '{title}'")
                return {
                    "suggested_team_id": data.get("suggested_team_id", team_id),
                    "recommended_action": data.get("recommended_action"),
                    "confidence": float(data.get("confidence", 0.92)),
                }
        except Exception as exc:
            logger.warning(f"OpenAI action synthesis failed, falling back to deterministic: {exc}")

    # --- Deterministic Fallback Rules ---
    title_lower = title.lower()
    if "face id" in title_lower or "biometric" in title_lower or "crash" in title_lower:
        action = (
            "1. Inspect mobile crash logs (Crashlytics/Sentry) for SIGSEGV / nil unwrapping in BiometricAuthHandler.\n"
            "2. Reproduce Face ID prompt flow on iOS 18.x physical test devices.\n"
            "3. Prepare hotfix patch with defensive fallback to passcode if biometric evaluation fails."
        )
        confidence = 0.95
    elif "lounge" in title_lower or "crowd" in title_lower:
        action = (
            "1. Review hourly check-in volumes and waitlist queue duration at airport lounge desks.\n"
            "2. Enable app push notifications notifying cardholders of real-time lounge occupancy levels.\n"
            "3. Coordinate with ground operations to optimize ingress flow during morning flight banks."
        )
        confidence = 0.90
    elif "virtual" in title_lower or "eno" in title_lower:
        action = (
            "1. Audit virtual card authorization logs with partner payment networks for decline codes.\n"
            "2. Verify client-side autofill payload format for address and CVC inputs.\n"
            "3. Update user-facing error messaging if merchant restricts virtual BIN ranges."
        )
        confidence = 0.88
    elif "shopping" in title_lower or "extension" in title_lower:
        action = (
            "1. Profile content script CPU and memory usage across top 50 e-commerce domains.\n"
            "2. Throttle DOM mutation observer frequency during coupon verification steps.\n"
            "3. Release browser extension patch v2.4.1 to Chrome Web Store."
        )
        confidence = 0.92
    else:
        action = (
            f"1. Triage customer feedback with {team_id} engineering leads.\n"
            f"2. Pull system metrics for {product_id} over the active period.\n"
            "3. Determine if immediate mitigation or documentation clarification is required."
        )
        confidence = 0.85

    return {
        "suggested_team_id": team_id,
        "recommended_action": action,
        "confidence": confidence,
    }


def compliance_reflector_node(state: InvestigationState) -> Dict[str, Any]:
    """Node 4: Compliance & Separation Reflector Agent. Enforces strict Evidence vs. Hypothesis boundaries via LLM critique."""
    client = _get_openai_client(state)
    hypothesis = state.get("investigation_hypothesis", "")
    evidence = state.get("observed_evidence", "")
    iteration = state.get("iteration_count", 0)
    model = state.get("model_name") or settings.LLM_MODEL or "gpt-4o-mini"

    # Fast deterministic phrase rejection
    has_certainty_violation = any(phrase in hypothesis.lower() for phrase in CERTAINTY_PHRASES)

    # --- Live OpenAI GPT-4o-mini Reflection Critique ---
    if client:
        try:
            prompt = (
                f"Observed Customer Evidence:\n{evidence}\n\n"
                f"Investigation Hypothesis:\n{hypothesis}\n\n"
                "Evaluate if the hypothesis strictly follows the Responsible AI guardrail: "
                "It MUST be framed tentatively as an unverified investigation hypothesis and NEVER claim a confirmed bug or proven fact. "
                "Return JSON: {\"compliance_passed\": bool, \"reflection_notes\": string, \"refined_hypothesis\": string}"
            )
            response = client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": INVESTIGATION_REFLECTION_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
            )
            data = json.loads(response.choices[0].message.content or "{}")
            compliance_passed = bool(data.get("compliance_passed", True)) and not has_certainty_violation

            if not compliance_passed:
                refined = data.get("refined_hypothesis") or f"Hypothesis: Investigate potential system anomalies. Specifically verify: {hypothesis}"
                logger.warning(f"Compliance reflection rephrased hypothesis via OpenAI critique: {data.get('reflection_notes')}")
                return {
                    "compliance_passed": False,
                    "reflection_notes": data.get("reflection_notes", "LLM Reflection detected certainty violation; refined hypothesis."),
                    "investigation_hypothesis": refined,
                    "iteration_count": iteration + 1,
                }
            return {
                "compliance_passed": True,
                "reflection_notes": data.get("reflection_notes", "Passed OpenAI compliance reflection critique."),
                "iteration_count": iteration + 1,
            }
        except Exception as exc:
            logger.warning(f"OpenAI compliance reflection critique failed, falling back to regex: {exc}")

    # --- Deterministic Fallback Guardrails ---
    is_tentative = any(
        kw in hypothesis.lower()
        for kw in ["hypothesis:", "investigate", "potential", "plausible", "verify whether", "possible"]
    )

    if has_certainty_violation or not is_tentative:
        rephrased = f"Hypothesis: Investigate potential system anomalies. Specifically verify: {hypothesis}"
        logger.warning(
            "Compliance reflection detected non-compliant hypothesis phrasing. Reframing.",
            cluster_id=state.get("cluster_id"),
            iteration=iteration,
        )
        return {
            "compliance_passed": False,
            "reflection_notes": "Rejected definitive phrasing; enforced tentative investigative framing.",
            "investigation_hypothesis": rephrased,
            "iteration_count": iteration + 1,
        }

    return {
        "compliance_passed": True,
        "reflection_notes": "Passed Responsible AI guardrail. Strict Evidence vs. Hypothesis separation verified.",
        "iteration_count": iteration + 1,
    }


def hitl_checkpoint_node(state: InvestigationState) -> Dict[str, Any]:
    """Node 5: Human-in-the-Loop Checkpoint. Sets status to 'pending_approval' for human operator review."""
    return {"status": "pending_approval"}


def check_compliance_edge(state: InvestigationState) -> str:
    """Conditional edge deciding whether to loop back for hypothesis refinement or proceed to checkpoint."""
    if not state.get("compliance_passed", False) and state.get("iteration_count", 0) < 2:
        return "generate_hypotheses"
    return "hitl_checkpoint"


def build_investigation_graph():
    """Construct and compile the multi-agent LangGraph state machine with memory checkpointer."""
    workflow = StateGraph(InvestigationState)

    workflow.add_node("gather_evidence", gather_evidence_node)
    workflow.add_node("generate_hypotheses", generate_hypotheses_node)
    workflow.add_node("synthesize_action_plan", synthesize_action_plan_node)
    workflow.add_node("compliance_reflector", compliance_reflector_node)
    workflow.add_node("hitl_checkpoint", hitl_checkpoint_node)

    workflow.add_edge(START, "gather_evidence")
    workflow.add_edge("gather_evidence", "generate_hypotheses")
    workflow.add_edge("generate_hypotheses", "synthesize_action_plan")
    workflow.add_edge("synthesize_action_plan", "compliance_reflector")
    workflow.add_conditional_edges(
        "compliance_reflector",
        check_compliance_edge,
        {
            "generate_hypotheses": "generate_hypotheses",
            "hitl_checkpoint": "hitl_checkpoint",
        },
    )
    workflow.add_edge("hitl_checkpoint", END)

    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Compiled singleton graph
investigation_graph = build_investigation_graph()
