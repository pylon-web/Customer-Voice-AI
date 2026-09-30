"""Configurable Team Routing Engine Service.

Evaluates database routing rules, calculates SLAs, priority levels, remediation playbooks,
and public review response guidance for customer review clusters.
"""

from typing import Optional, List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.errors import NotFoundError, ValidationError
from app.models.entities import IssueCluster, Team, TeamRoutingRule, Recommendation
from app.models.schemas import (
    RoutedTeamAssignment,
    RoutingEvaluationRequest,
    TeamRead,
    TeamRoutingRuleRead,
)
from app.repositories.team_repo import TeamRepository, TEAM_ALIAS_MAP
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.trend_repo import TrendRepository
from app.repositories.recommendation_repo import RecommendationRepository

logger = get_logger("cva.service.routing")

# Team-specific remediation playbooks
TEAM_PLAYBOOKS: Dict[str, List[str]] = {
    "digital_engineering_mobile": [
        "1. Triage Crashlytics/Sentry logs for unhandled exceptions or null dereferences.",
        "2. Reproduce user flow on physical iOS/Android test matrix matching reported OS versions.",
        "3. Verify biometric, keychain, and push notification entitlements.",
        "4. Implement defensive fallback to PIN/passcode if biometric authentication errors occur.",
        "5. Deploy hotfix build to TestFlight / internal beta channel and monitor crash-free sessions.",
    ],
    "travel_lounges_product": [
        "1. Review hourly lounge ingress telemetries against departing flight bank density.",
        "2. Throttle digital waitlist admission rate to preserve physical seating capacity.",
        "3. Deploy live occupancy warning banners inside Capital One Travel mobile portal.",
        "4. Coordinate with airport station managers to distribute overflow beverage vouchers.",
    ],
    "payments_operations": [
        "1. Audit payment gateway transaction logs for merchant rejection codes.",
        "2. Review clearinghouse cut-off times and pending authorization hold windows.",
        "3. Verify fee assessment logic against zero-fee checking account rules.",
        "4. Process automated fee waivers for affected cardholders in good standing.",
    ],
    "cafe_operations": [
        "1. Clear guest Wi-Fi DHCP lease pool exhaustion and restart captive portal controller.",
        "2. Test access point signal strength and latency across high-occupancy seating zones.",
        "3. Audit on-site ATM cash levels and card reader diagnostics.",
        "4. Retrain café ambassadors on contactless Peet's beverage discount scanning.",
    ],
    "digital_ai_security": [
        "1. Inspect virtual card number tokenization logs with merchant gateway networks.",
        "2. Calibrate fraud anomaly detection scoring model to reduce false-positive card locks.",
        "3. Retrain Eno NLP intent classifier for ambiguous transaction inquiries.",
        "4. Update customer-facing error messages when merchants restrict virtual BIN ranges.",
    ],
    "shopping_engineering": [
        "1. Profile content script DOM mutation observers on reported e-commerce partner domains.",
        "2. Throttle coupon code auto-injection polling intervals to 250ms.",
        "3. Verify affiliate cashback tracking attribution webhooks and cookie lifespans.",
        "4. Publish updated extension package v2.4.2 to Chrome Web Store.",
    ],
    "customer_experience": [
        "1. Review IVR phone routing tree and customer service queue hold time distributions.",
        "2. Identify recurring friction points and update customer support knowledge base articles.",
        "3. Escalate high-urgency unresolved complaints to senior resolution specialists.",
        "4. Provide proactive outreach to accounts impacted by systemic service delays.",
    ],
}

# Team-specific public review response guidance templates
TEAM_REVIEW_RESPONSES: Dict[str, str] = {
    "digital_engineering_mobile": (
        "App Store / Play Store Response Guidance: 'Thank you for reporting this issue. Our mobile engineering "
        "team has identified the startup issue in the latest update and released an urgent hotfix patch. "
        "Please update your app from the store to restore normal functionality. If issues persist, reach out to "
        "mobile-support@capitalone.com.'"
    ),
    "travel_lounges_product": (
        "Public Review Response Guidance: 'We sincerely apologize for the crowding you experienced during your visit. "
        "We are actively managing peak flight bank capacity and expanding live wait-time tracking in the Capital One app "
        "so cardholders can plan visits smoothly. We'd love to make this right—please contact travel-support@capitalone.com.'"
    ),
    "payments_operations": (
        "Public Review Response Guidance: 'We understand how frustrating unexpected transaction declines or fee charges can be. "
        "We are reviewing your account history to ensure fees are applied accurately according to our zero-fee checking policy. "
        "Please contact 360-support@capitalone.com for immediate account assistance.'"
    ),
    "cafe_operations": (
        "Google Places / Yelp Response Guidance: 'We're sorry your visit to our Capital One Café didn't meet expectations! "
        "We have upgraded our Wi-Fi access points to improve reliability. Next time you visit, enjoy a handcrafted beverage "
        "on us—speak with any ambassador on site.'"
    ),
    "digital_ai_security": (
        "Public Review Response Guidance: 'Security is our top priority, but we regret that your virtual card was declined at checkout. "
        "We have updated our merchant compatibility settings to prevent unexpected blocks. Please reach out to "
        "eno-support@capitalone.com if you need an immediate replacement card.'"
    ),
    "shopping_engineering": (
        "Chrome Web Store Response Guidance: 'Thanks for flagging this extension issue! We have released an update addressing "
        "browser slowdowns during checkout. Please update the extension in Chrome Web Store to enjoy automatic coupon savings "
        "without delay.'"
    ),
    "customer_experience": (
        "Public Review Response Guidance: 'We sincerely apologize for the hold time you experienced. We value your time and "
        "are expanding support coverage during peak hours. A senior representative is available to assist you directly at "
        "1-800-CAPITAL.'"
    ),
}


class RoutingService:
    """Orchestrates dynamic rule evaluation, priority assignment, SLAs, and playbooks."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepository(session)
        self.cluster_repo = ClusterRepository(session)
        self.trend_repo = TrendRepository(session)
        self.rec_repo = RecommendationRepository(session)

    def _determine_priority_and_sla(
        self,
        anomaly_score: float,
        wow_change_pct: float,
        negative_pct: float,
        severity: str = "medium",
    ) -> Tuple[str, int]:
        """Compute SLA hours and priority level based on velocity anomaly score and severity."""
        sev = severity.lower()
        if anomaly_score >= 3.0 or (wow_change_pct >= 100.0 and sev in ("critical", "high")):
            return "P1_CRITICAL", 24
        elif anomaly_score >= 2.0 or wow_change_pct >= 25.0 or sev == "critical":
            return "P2_HIGH", 48
        elif wow_change_pct > 0 or negative_pct >= 60.0 or sev == "high":
            return "P3_MEDIUM", 72
        else:
            return "P4_LOW", 168

    async def route_cluster(self, cluster_id: str) -> RoutedTeamAssignment:
        """Route an issue cluster to the appropriate business team using dynamic database rules."""
        cluster = await self.cluster_repo.get_by_id(cluster_id)
        if not cluster:
            raise NotFoundError(resource="IssueCluster", identifier=cluster_id)

        # 1. Fetch velocity trend
        trend = await self.trend_repo.get_latest_by_cluster_id(cluster_id)
        anomaly_score = trend.anomaly_score if trend else 0.0
        wow_change_pct = trend.wow_change_pct if trend else 0.0

        # 2. Build search corpus from cluster data
        corpus = [
            cluster.affected_product_id,
            cluster.category,
            cluster.cluster_title,
        ]
        if cluster.representative_quotes:
            corpus.extend(cluster.representative_quotes)

        # 3. Match against dynamic database routing rules
        matched_team, matched_rule, match_reason = await self.team_repo.match_team_rule(corpus)

        # 4. Compute priority & SLA
        priority_level, sla_hours = self._determine_priority_and_sla(
            anomaly_score=anomaly_score,
            wow_change_pct=wow_change_pct,
            negative_pct=cluster.negative_pct,
            severity="critical" if anomaly_score >= 2.0 else "medium",
        )

        # 5. Attach playbooks and review response guidance
        canonical_team_id = TEAM_ALIAS_MAP.get(matched_team.id, matched_team.id)
        playbook = TEAM_PLAYBOOKS.get(canonical_team_id, TEAM_PLAYBOOKS["customer_experience"])
        review_response = TEAM_REVIEW_RESPONSES.get(canonical_team_id, TEAM_REVIEW_RESPONSES["customer_experience"])

        # 6. Update Recommendation if one exists for this cluster
        rec = await self.rec_repo.get_by_cluster_id(cluster_id)
        if rec and rec.suggested_team_id != matched_team.id:
            rec.suggested_team_id = matched_team.id
            await self.session.commit()

        logger.info(
            f"Routed cluster '{cluster.cluster_title}' to team '{matched_team.name}'",
            extra={
                "cluster_id": cluster.id,
                "team_id": matched_team.id,
                "priority": priority_level,
                "sla_hours": sla_hours,
            },
        )

        return RoutedTeamAssignment(
            cluster_id=cluster.id,
            matched_team=TeamRead.model_validate(matched_team),
            matched_rule_id=matched_rule.id if matched_rule else None,
            matched_pattern=matched_rule.pattern if matched_rule else "fallback",
            match_reason=match_reason,
            priority_level=priority_level,
            target_sla_hours=sla_hours,
            remediation_playbook=playbook,
            review_response_guidance=review_response,
        )

    async def evaluate_routing(self, request: RoutingEvaluationRequest) -> RoutedTeamAssignment:
        """Evaluate routing for an existing cluster or hypothetical issue."""
        if request.cluster_id:
            return await self.route_cluster(request.cluster_id)

        # Hypothetical evaluation
        corpus = [
            request.product_id or "",
            request.category or "",
            request.issue_text or "",
        ]
        matched_team, matched_rule, match_reason = await self.team_repo.match_team_rule(corpus)

        priority_level, sla_hours = self._determine_priority_and_sla(
            anomaly_score=request.anomaly_score or 0.0,
            wow_change_pct=0.0,
            negative_pct=80.0,
            severity=request.severity or "medium",
        )

        canonical_team_id = TEAM_ALIAS_MAP.get(matched_team.id, matched_team.id)
        playbook = TEAM_PLAYBOOKS.get(canonical_team_id, TEAM_PLAYBOOKS["customer_experience"])
        review_response = TEAM_REVIEW_RESPONSES.get(canonical_team_id, TEAM_REVIEW_RESPONSES["customer_experience"])

        return RoutedTeamAssignment(
            cluster_id=None,
            matched_team=TeamRead.model_validate(matched_team),
            matched_rule_id=matched_rule.id if matched_rule else None,
            matched_pattern=matched_rule.pattern if matched_rule else "fallback",
            match_reason=match_reason,
            priority_level=priority_level,
            target_sla_hours=sla_hours,
            remediation_playbook=playbook,
            review_response_guidance=review_response,
        )

    async def create_rule(self, team_id: str, pattern: str, priority: int = 1) -> TeamRoutingRule:
        """Create a new dynamic routing rule."""
        team = await self.team_repo.get_team_by_id(team_id)
        if not team:
            raise NotFoundError(resource="Team", identifier=team_id)

        rule = await self.team_repo.create_routing_rule(team_id=team.id, pattern=pattern, priority=priority)
        await self.session.commit()
        return rule

    async def delete_rule(self, rule_id: str) -> bool:
        """Delete an existing routing rule."""
        success = await self.team_repo.delete_routing_rule(rule_id)
        if not success:
            raise NotFoundError(resource="TeamRoutingRule", identifier=rule_id)
        await self.session.commit()
        return True
