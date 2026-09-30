"""Investigation agent interface, Mock, and OpenAI implementations for root cause analysis."""

import abc
from typing import Dict, Any, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.agents.investigation_graph import (
    investigation_graph,
    InvestigationState,
)

logger = get_logger("cva.agent.investigation")


class InvestigationAgent(abc.ABC):
    """Abstract base class for root cause investigation agents."""

    @abc.abstractmethod
    async def investigate(self, initial_state: InvestigationState) -> InvestigationState:
        """Run root cause investigation state machine across an issue cluster."""
        pass


class MockInvestigationAgent(InvestigationAgent):
    """Deterministic LangGraph investigation agent for high-speed offline execution and automated tests."""

    async def investigate(self, initial_state: InvestigationState) -> InvestigationState:
        thread_id = initial_state.get("cluster_id", "default_thread")
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(
            f"Invoking MockInvestigationAgent LangGraph for cluster {initial_state.get('cluster_id')}",
            cluster_title=initial_state.get("cluster_title"),
        )
        final_state: InvestigationState = investigation_graph.invoke(initial_state, config=config)
        return final_state


class OpenAIInvestigationAgent(InvestigationAgent):
    """OpenAI GPT-4o-mini investigation agent utilizing full multi-agent LangGraph execution."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.LLM_MODEL or "gpt-4o-mini"
        self._fallback_agent = MockInvestigationAgent()

    async def investigate(self, initial_state: InvestigationState) -> InvestigationState:
        # If API key is mock or placeholder, gracefully fall back to deterministic graph
        if not self.api_key or "mock" in self.api_key.lower():
            logger.info("Using deterministic graph fallback due to mock API key.")
            return await self._fallback_agent.investigate(initial_state)

        # Inject runtime OpenAI config into the state for LangGraph nodes
        state_with_llm: InvestigationState = {
            **initial_state,
            "llm_provider": "openai",
            "openai_api_key": self.api_key,
            "model_name": self.model,
            "iteration_count": initial_state.get("iteration_count", 0),
        }

        thread_id = initial_state.get("cluster_id", "default_thread")
        config = {"configurable": {"thread_id": thread_id}}

        logger.info(
            f"Invoking OpenAIInvestigationAgent LangGraph with real GPT-4o-mini for cluster {initial_state.get('cluster_id')}",
            cluster_title=initial_state.get("cluster_title"),
            model=self.model,
        )

        try:
            # Execute full multi-agent state graph with OpenAI-powered nodes
            final_state: InvestigationState = investigation_graph.invoke(state_with_llm, config=config)
            return final_state
        except Exception as exc:
            logger.error("OpenAI LangGraph investigation failed, falling back to deterministic graph", error=str(exc))
            return await self._fallback_agent.investigate(initial_state)


def get_investigation_agent() -> InvestigationAgent:
    """Factory returning configured investigation agent."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        return OpenAIInvestigationAgent()
    return MockInvestigationAgent()
