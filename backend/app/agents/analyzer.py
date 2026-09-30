"""AI Review Analysis Agent with deterministic Mock and OpenAI GPT-4o-mini implementations."""

import abc
import json
import re
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.prompts import ANALYSIS_SYSTEM_PROMPT, build_review_analysis_prompt

logger = get_logger("cva.agent.analyzer")


class AnalysisResult(BaseModel):
    """Structured extraction output from the review analysis agent."""

    sentiment: Literal["positive", "neutral", "negative"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    category: str
    issue: str
    severity: Literal["low", "medium", "high", "critical"]
    customer_intent: Literal["bug_report", "complaint", "feature_request", "praise", "question"]
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.95)


class BaseAnalysisAgent(abc.ABC):
    """Abstract base class for review analysis agents."""

    @abc.abstractmethod
    async def analyze(
        self,
        text: str,
        rating: int,
        product_id: str,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> AnalysisResult:
        """Analyze a customer review and return structured intelligence."""
        pass


class MockAnalysisAgent(BaseAnalysisAgent):
    """Deterministic, rule-based analysis agent for ultra-fast, zero-cost offline analysis and tests."""

    async def analyze(
        self,
        text: str,
        rating: int,
        product_id: str,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> AnalysisResult:
        combined = f"{title or ''} {text}".lower()

        # 1. Sentiment & Sentiment Score
        if rating >= 4:
            sentiment = "positive"
            sentiment_score = 0.90 if rating == 5 else 0.65
        elif rating == 3:
            sentiment = "neutral"
            sentiment_score = 0.05
        else:
            sentiment = "negative"
            sentiment_score = -0.90 if rating == 1 else -0.60

        # Adjust score slightly if intense keywords present
        if "horrible" in combined or "terrible" in combined or "unusable" in combined:
            sentiment_score = max(-1.0, sentiment_score - 0.1)
        elif "outstanding" in combined or "excellent" in combined or "flawless" in combined:
            sentiment_score = min(1.0, sentiment_score + 0.1)

        # 2. Extract Named Entities
        entities: List[Dict[str, Any]] = []
        for airport in ["DFW", "IAD", "DEN", "JFK", "LAX", "ORD"]:
            if airport.lower() in combined:
                entities.append({"name": airport, "type": "airport"})
        for os_name in ["ios 18", "ios", "android 15", "android"]:
            if os_name in combined:
                entities.append({"name": os_name.upper(), "type": "operating_system"})
        if "v6.14" in combined or "6.14" in combined:
            entities.append({"name": "v6.14", "type": "app_version"})
        if location:
            entities.append({"name": location, "type": "location"})

        # 3. Categorization & Issue Identification
        if any(w in combined for w in ["face id", "touch id", "biometric", "login", "logging out", "authenticat"]) or "fingerprint" in combined:
            category = "Authentication & Biometrics"
            issue = "Face ID biometric authentication failure or crash"
            severity = "critical" if rating <= 2 else "medium"
            intent = "bug_report" if ("crash" in combined or rating <= 2) else "question"

        elif any(w in combined for w in ["lounge", "priority pass", "waitlist", "crowd"]) or (bool(re.search(r"\b(line|lines|queue)\b", combined)) and "terminal" in combined):
            category = "Travel & Lounge Perks"
            if "crowd" in combined or "line" in combined or "wait" in combined:
                issue = "Lounge crowding and access wait times"
            else:
                issue = "Lounge amenities and travel perks"
            severity = "high" if rating <= 2 else ("medium" if rating == 3 else "low")
            intent = "complaint" if rating <= 3 else "praise"

        elif any(w in combined for w in ["virtual card", "eno"]) or product_id == "eno_virtual_assistant":
            category = "Eno & Virtual Assistant"
            issue = "Virtual card generation or merchant acceptance failure"
            severity = "high" if rating <= 2 else "medium"
            intent = "complaint" if rating <= 3 else "feature_request"

        elif any(w in combined for w in ["extension", "chrome", "shopping", "coupon"]) or product_id == "c1_shopping_extension":
            category = "Shopping Extension"
            issue = "Shopping browser extension freeze during checkout"
            severity = "high" if rating <= 2 else "medium"
            intent = "bug_report" if "freeze" in combined else "complaint"

        elif any(w in combined for w in ["wifi", "wi-fi", "internet", "coffee", "ambassador", "cafe"]) or product_id in ["c1_cafe", "c1_branch_network"]:
            category = "Café Facilities & Wi-Fi"
            if "wifi" in combined or "wi-fi" in combined or "internet" in combined:
                issue = "Café Wi-Fi network connectivity interruption"
                severity = "medium" if rating <= 3 else "low"
                intent = "complaint" if rating <= 3 else "praise"
            else:
                issue = "Café ambiance, seating, or beverage experience"
                severity = "low"
                intent = "praise" if rating >= 4 else "complaint"

        elif any(w in combined for w in ["cashback", "cash back", "rewards", "dining", "points", "miles", "groceries"]) or (product_id in ["savor_one", "venture_x", "venture", "quicksilver", "platinum"] and not any(w in combined for w in ["surcharge", "overdraft", "conversion", "stagnant"])):
            category = "Rewards & Cash Back"
            issue = "Rewards earning, cash back percentage, or points redemption"
            severity = "high" if rating <= 2 else ("medium" if rating == 3 else "low")
            intent = "complaint" if rating <= 3 else "praise"

        elif any(w in combined for w in ["overdraft", "surcharge", "foreign", "conversion", "wire fee", "late fee", "penalty", "hidden fee"]):
            category = "Overdraft & Fees"
            issue = "Fee disclosure and transaction surcharges"
            severity = "high" if rating <= 2 else "medium"
            intent = "complaint"

        elif any(w in combined for w in ["credit score", "creditwise", "tracker", "transunion", "experian", "score monitoring"]) or product_id == "creditwise":
            category = "Credit Tracking & Score"
            issue = "Free credit score monitoring updates and identity tracking"
            severity = "medium" if rating <= 3 else "low"
            intent = "complaint" if rating <= 3 else "praise"

        elif any(w in combined for w in ["deposit", "atm", "check", "savings", "checking", "transfer"]) or product_id in ["banking_360_checking", "banking_360_savings", "banking_360_cd"]:
            category = "360 Banking & Accounts"
            issue = "Check deposit, ATM availability, or funds clearance"
            severity = "high" if rating <= 2 else ("medium" if rating == 3 else "low")
            intent = "complaint" if rating <= 3 else "praise"

        elif any(w in combined for w in ["crash", "freeze", "bug", "glitch", "error", "broken"]):
            category = "Mobile App"
            issue = "Mobile application stability and crash errors"
            severity = "critical" if rating == 1 else "high"
            intent = "bug_report"

        elif rating >= 4:
            category = "Customer Support & Service"
            issue = "High customer satisfaction and reliable performance"
            severity = "low"
            intent = "praise"

        else:
            category = "Account Management"
            issue = "General account management and feature usability"
            severity = "medium" if rating <= 2 else "low"
            intent = "complaint" if rating <= 2 else "question"

        return AnalysisResult(
            sentiment=sentiment,
            sentiment_score=round(sentiment_score, 2),
            category=category,
            issue=issue,
            severity=severity,
            customer_intent=intent,
            entities=entities,
            confidence=0.96,
        )


class OpenAIAnalysisAgent(BaseAnalysisAgent):
    """Production AI analysis agent leveraging OpenAI GPT-4o-mini structured JSON outputs."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL
        self._fallback_agent = MockAnalysisAgent()

    async def analyze(
        self,
        text: str,
        rating: int,
        product_id: str,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> AnalysisResult:
        if not self.api_key or self.api_key in ("mock-api-key", ""):
            logger.info("OpenAI API key not configured. Using deterministic mock agent fallback.")
            return await self._fallback_agent.analyze(text, rating, product_id, title, location)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            prompt = build_review_analysis_prompt(text, rating, product_id, title, location)

            response = await client.chat.completions.create(
                model=self.model,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )

            raw_json = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_json)
            return AnalysisResult.model_validate(parsed)

        except Exception as exc:
            logger.warning(
                "OpenAI LLM analysis failed. Falling back to deterministic mock agent.",
                error=str(exc),
            )
            return await self._fallback_agent.analyze(text, rating, product_id, title, location)


def get_analysis_agent(provider: Optional[str] = None) -> BaseAnalysisAgent:
    """Factory creating configured AI analysis agent."""
    active_provider = provider or settings.LLM_PROVIDER
    if active_provider.lower() == "openai":
        return OpenAIAnalysisAgent()
    return MockAnalysisAgent()
