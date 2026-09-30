"""Team management, configurable routing rules, and intelligent assignment REST API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.errors import NotFoundError
from app.services.routing_service import RoutingService
from app.repositories.team_repo import TeamRepository
from app.models.schemas import (
    TeamRead,
    TeamWithRulesRead,
    TeamRoutingRuleRead,
    TeamRoutingRuleCreate,
    RoutedTeamAssignment,
    RoutingEvaluationRequest,
)

router = APIRouter(tags=["Team Routing & Rules"])


def _to_team_with_rules_read(team) -> TeamWithRulesRead:
    """Format Team ORM model to schema with routing rules safely."""
    rules = []
    if "routing_rules" in getattr(team, "__dict__", {}) and team.__dict__["routing_rules"]:
        rules = [
            TeamRoutingRuleRead(
                id=r.id,
                team_id=r.team_id,
                pattern=r.pattern,
                priority=r.priority,
                created_at=r.created_at,
                team_name=team.name,
            )
            for r in team.__dict__["routing_rules"]
        ]
    return TeamWithRulesRead(
        id=team.id,
        name=team.name,
        lead_email=team.lead_email,
        slack_channel=team.slack_channel,
        is_active=team.is_active,
        routing_rules=rules,
    )


def _to_rule_read(rule) -> TeamRoutingRuleRead:
    """Format TeamRoutingRule ORM model to schema safely."""
    team_name = rule.team.name if "team" in getattr(rule, "__dict__", {}) and rule.__dict__["team"] else None
    return TeamRoutingRuleRead(
        id=rule.id,
        team_id=rule.team_id,
        pattern=rule.pattern,
        priority=rule.priority,
        created_at=rule.created_at,
        team_name=team_name,
    )


# ------------------------------------------------------------------------------
# Teams Endpoints
# ------------------------------------------------------------------------------
@router.get(
    "/teams",
    response_model=List[TeamWithRulesRead],
    status_code=status.HTTP_200_OK,
    summary="List All Business Teams",
    description="Retrieve all 7 generic business teams with their active routing rules and contact details.",
)
async def list_teams(
    session: AsyncSession = Depends(get_async_session),
) -> List[TeamWithRulesRead]:
    """List business teams and active routing patterns."""
    repo = TeamRepository(session)
    teams = await repo.get_all_teams()
    return [_to_team_with_rules_read(t) for t in teams]


@router.get(
    "/teams/{team_id}",
    response_model=TeamWithRulesRead,
    status_code=status.HTTP_200_OK,
    summary="Get Business Team Details",
    description="Fetch single team details and assigned routing rules by team ID or alias.",
)
async def get_team_by_id(
    team_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> TeamWithRulesRead:
    """Fetch team by ID with routing rules."""
    repo = TeamRepository(session)
    team = await repo.get_team_by_id(team_id)
    if not team:
        raise NotFoundError(resource="Team", identifier=team_id)
    return _to_team_with_rules_read(team)


# ------------------------------------------------------------------------------
# Dynamic Routing Rules Management
# ------------------------------------------------------------------------------
@router.get(
    "/routing/rules",
    response_model=List[TeamRoutingRuleRead],
    status_code=status.HTTP_200_OK,
    summary="List Configured Routing Rules",
    description="Retrieve all dynamic database routing rules ordered by priority descending.",
)
async def list_routing_rules(
    session: AsyncSession = Depends(get_async_session),
) -> List[TeamRoutingRuleRead]:
    """List all dynamic routing rules."""
    repo = TeamRepository(session)
    rules = await repo.get_routing_rules()
    return [_to_rule_read(r) for r in rules]


@router.post(
    "/routing/rules",
    response_model=TeamRoutingRuleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dynamic Routing Rule",
    description="Add a new pattern matching rule to route specific products or issues to a designated team.",
)
async def create_routing_rule(
    payload: TeamRoutingRuleCreate,
    session: AsyncSession = Depends(get_async_session),
) -> TeamRoutingRuleRead:
    """Create a new dynamic routing rule."""
    service = RoutingService(session)
    rule = await service.create_rule(
        team_id=payload.team_id,
        pattern=payload.pattern,
        priority=payload.priority,
    )
    return _to_rule_read(rule)


@router.delete(
    "/routing/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Routing Rule",
    description="Remove an existing routing rule by ID without requiring code deployment.",
)
async def delete_routing_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Delete routing rule by ID."""
    service = RoutingService(session)
    await service.delete_rule(rule_id)


# ------------------------------------------------------------------------------
# Routing Evaluation & Assignment
# ------------------------------------------------------------------------------
@router.post(
    "/routing/evaluate",
    response_model=RoutedTeamAssignment,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Dynamic Routing Rules",
    description="Test routing rules against a cluster ID or arbitrary hypothetical issue feedback.",
)
async def evaluate_routing(
    payload: RoutingEvaluationRequest,
    session: AsyncSession = Depends(get_async_session),
) -> RoutedTeamAssignment:
    """Evaluate routing match for an issue or cluster."""
    service = RoutingService(session)
    return await service.evaluate_routing(payload)


@router.post(
    "/routing/clusters/{cluster_id}",
    response_model=RoutedTeamAssignment,
    status_code=status.HTTP_200_OK,
    summary="Route Issue Cluster to Business Team",
    description="Evaluates dynamic rules for a cluster, determines team, assigns SLA/priority, and attaches playbooks.",
)
async def route_issue_cluster(
    cluster_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> RoutedTeamAssignment:
    """Route a specific issue cluster to its owning enterprise team."""
    service = RoutingService(session)
    return await service.route_cluster(cluster_id)
