"""Repository for team management and dynamic routing rule matching."""

from typing import List, Optional, Tuple, Dict
from sqlalchemy import select, desc, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Team, TeamRoutingRule, Product, Source
from app.models.seeds import CAPITAL_ONE_PRODUCTS, INGESTION_SOURCES, BUSINESS_TEAMS

TEAM_ALIAS_MAP: Dict[str, str] = {
    "digital_eng_mobile": "digital_engineering_mobile",
    "digital_engineering_mobile": "digital_engineering_mobile",
    "payments_ops": "payments_operations",
    "payments_operations": "payments_operations",
    "travel_lounges_prod": "travel_lounges_product",
    "travel_lounges_product": "travel_lounges_product",
    "cafe_ops": "cafe_operations",
    "cafe_operations": "cafe_operations",
    "digital_ai_security": "digital_ai_security",
    "shopping_eng": "shopping_engineering",
    "shopping_engineering": "shopping_engineering",
    "customer_exp": "customer_experience",
    "customer_experience": "customer_experience",
}


class TeamRepository:
    """Data access repository for teams and configurable routing rules."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_teams(self) -> List[Team]:
        """Fetch all active teams with their routing rules."""
        stmt = (
            select(Team)
            .options(selectinload(Team.routing_rules))
            .where(Team.is_active == True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_team_by_id(self, team_id: str) -> Optional[Team]:
        """Fetch team by ID or canonical alias with its active routing rules."""
        canonical_id = TEAM_ALIAS_MAP.get(team_id, team_id)
        stmt = (
            select(Team)
            .options(selectinload(Team.routing_rules))
            .where(Team.id == canonical_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_routing_rules(self) -> List[TeamRoutingRule]:
        """Fetch all dynamic routing rules ordered by priority descending."""
        stmt = (
            select(TeamRoutingRule)
            .options(selectinload(TeamRoutingRule.team))
            .order_by(desc(TeamRoutingRule.priority), desc(TeamRoutingRule.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_rule_by_id(self, rule_id: str) -> Optional[TeamRoutingRule]:
        """Fetch single routing rule by ID."""
        stmt = (
            select(TeamRoutingRule)
            .options(selectinload(TeamRoutingRule.team))
            .where(TeamRoutingRule.id == rule_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_routing_rule(self, team_id: str, pattern: str, priority: int = 1) -> TeamRoutingRule:
        """Create and persist a new routing rule."""
        canonical_id = TEAM_ALIAS_MAP.get(team_id, team_id)
        rule = TeamRoutingRule(
            team_id=canonical_id,
            pattern=pattern.strip().lower(),
            priority=priority,
        )
        self.session.add(rule)
        await self.session.flush()
        # Eager load the attached team
        loaded = await self.get_rule_by_id(rule.id)
        return loaded or rule

    async def delete_routing_rule(self, rule_id: str) -> bool:
        """Delete a routing rule by ID."""
        rule = await self.get_rule_by_id(rule_id)
        if not rule:
            return False
        await self.session.delete(rule)
        await self.session.flush()
        return True

    async def match_team_for_issue(self, category: str, issue: str) -> Optional[Team]:
        """Find matching business team based on category and issue strings (backward compatibility)."""
        team, _, _ = await self.match_team_rule([category, issue])
        return team

    async def match_team_rule(self, search_corpus: List[str]) -> Tuple[Team, Optional[TeamRoutingRule], str]:
        """Evaluate routing rules against a list of text fields (product, category, title, quotes).

        Returns:
            Tuple[Team, Optional[TeamRoutingRule], str]: (Matched team, Matched rule if any, Match reason description)
        """
        rules = await self.get_routing_rules()
        normalized_corpus = [s.lower() for s in search_corpus if s]

        for rule in rules:
            pat = rule.pattern.lower()
            for text in normalized_corpus:
                if pat in text:
                    return rule.team, rule, f"Matched rule '{rule.pattern}' (Priority {rule.priority})"

        # Fallback to customer experience team
        fallback_team = await self.get_team_by_id("customer_experience")
        if not fallback_team:
            # If database not seeded yet, fallback to any active team
            all_teams = await self.get_all_teams()
            fallback_team = all_teams[0] if all_teams else None

        return fallback_team, None, "No specific routing rule pattern matched. Assigned to Customer Experience fallback."

    async def seed_initial_taxonomy_if_empty(self) -> None:
        """Seed Capital One products, sources, and business teams if database is empty."""
        # 1. Seed Products
        prod_check = await self.session.execute(select(Product).limit(1))
        if not prod_check.scalars().first():
            for p in CAPITAL_ONE_PRODUCTS:
                self.session.add(Product(**p))

        # 2. Seed Sources
        src_check = await self.session.execute(select(Source).limit(1))
        if not src_check.scalars().first():
            for s in INGESTION_SOURCES:
                self.session.add(Source(**s))

        # 3. Seed Teams & Routing Rules
        team_check = await self.session.execute(select(Team).limit(1))
        if not team_check.scalars().first():
            for t in BUSINESS_TEAMS:
                patterns = t.get("routing_patterns", [])
                team_obj = Team(
                    id=t["id"],
                    name=t["name"],
                    lead_email=t.get("lead_email"),
                    slack_channel=t.get("slack_channel"),
                    is_active=True,
                )
                self.session.add(team_obj)
                for prio, pattern in enumerate(patterns, start=1):
                    self.session.add(
                        TeamRoutingRule(
                            team_id=t["id"],
                            pattern=pattern,
                            priority=prio,
                        )
                    )

        await self.session.flush()
