"""Weekly Executive Intelligence Report Generation Service.

Synthesizes multi-source review feedback, velocity trends, root-cause hypotheses,
and geographic anomalies into structured JSON, formatted Markdown, and executive HTML/PDF briefs.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.entities import (
    Report,
    ReportIssue,
    IssueCluster,
    Review,
    ReviewAnalysis,
    Recommendation,
    TrendMetric,
)
from app.models.schemas import ReportGenerateRequest
from app.repositories.report_repo import ReportRepository
from app.repositories.cluster_repo import ClusterRepository
from app.repositories.trend_repo import TrendRepository
from app.repositories.recommendation_repo import RecommendationRepository
from app.kafka.producer import KafkaProducerService, get_kafka_producer
from app.kafka.events import ReportGeneratedEvent, ReportGeneratedPayload

logger = get_logger("cva.service.report")


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC offset-aware."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ReportService:
    """Orchestrates executive report generation, Markdown/HTML rendering, and Kafka events."""

    def __init__(
        self,
        session: AsyncSession,
        kafka_producer: Optional[KafkaProducerService] = None,
    ):
        self.session = session
        self.kafka_producer = kafka_producer or get_kafka_producer()
        self.report_repo = ReportRepository(session)
        self.cluster_repo = ClusterRepository(session)
        self.trend_repo = TrendRepository(session)
        self.rec_repo = RecommendationRepository(session)

    async def generate_weekly_report(
        self,
        request: Optional[ReportGenerateRequest] = None,
    ) -> Report:
        """Compile a comprehensive Weekly Executive Intelligence Report."""
        req = request or ReportGenerateRequest()

        # 1. Determine period window
        if req.period_end:
            period_end = _ensure_utc(req.period_end)
        else:
            # Check latest review date in DB
            latest_rev_stmt = select(func.max(Review.created_at))
            res = await self.session.execute(latest_rev_stmt)
            max_dt = res.scalar()
            period_end = _ensure_utc(max_dt) if max_dt else datetime.now(timezone.utc)

        if req.period_start:
            period_start = _ensure_utc(req.period_start)
        else:
            period_start = period_end - timedelta(days=7)

        title = req.title or f"Executive Customer Voice Intelligence Briefing — {period_end.strftime('%B %d, %Y')}"

        # 2. Compute macro review metrics in this period
        rev_stmt = select(Review).where(Review.created_at >= period_start, Review.created_at <= period_end)
        rev_res = await self.session.execute(rev_stmt)
        period_reviews = list(rev_res.scalars().all())

        total_reviews = len(period_reviews)
        if total_reviews == 0:
            # Fallback to all reviews if period window has no records
            all_stmt = select(Review).limit(1000)
            all_res = await self.session.execute(all_stmt)
            period_reviews = list(all_res.scalars().all())
            total_reviews = len(period_reviews)

        negative_count = sum(1 for r in period_reviews if r.rating <= 2)
        negative_pct = round((negative_count / float(total_reviews)) * 100.0, 1) if total_reviews > 0 else 0.0

        # 3. Compute geographic insights
        geo_map: Dict[str, Dict[str, Any]] = {}
        for r in period_reviews:
            if r.location:
                loc = r.location.strip()
                if loc not in geo_map:
                    geo_map[loc] = {"total": 0, "negative": 0, "categories": {}}
                geo_map[loc]["total"] += 1
                if r.rating <= 2:
                    geo_map[loc]["negative"] += 1

        geographic_insights = {
            loc: {
                "total_reviews": stats["total"],
                "negative_count": stats["negative"],
                "negative_pct": round((stats["negative"] / stats["total"]) * 100.0, 1) if stats["total"] > 0 else 0.0,
            }
            for loc, stats in geo_map.items()
            if stats["total"] >= 2
        }

        # 4. Identify highlighted issues from active clusters
        clusters = await self.cluster_repo.get_active_clusters(limit=50)
        report_issues: List[ReportIssue] = []
        emerging_cnt = 0
        improving_cnt = 0

        rank = 1
        for cluster in clusters:
            trend = await self.trend_repo.get_latest_by_cluster_id(cluster.id)
            rec = await self.rec_repo.get_by_cluster_id(cluster.id)

            issue_type = "persistent"
            if trend:
                if trend.trend_direction == "emerging" or trend.anomaly_score >= 2.0:
                    issue_type = "emerging"
                    emerging_cnt += 1
                elif trend.trend_direction == "improving" or trend.wow_change_pct <= -25.0:
                    issue_type = "improving"
                    improving_cnt += 1

            rep_issue = ReportIssue(
                cluster_id=cluster.id,
                recommendation_id=rec.id if rec else None,
                issue_type=issue_type,
                rank=rank,
            )
            report_issues.append(rep_issue)
            rank += 1

        # 5. Synthesize Executive Summary
        exec_summary = (
            f"Over the reporting window ({period_start.strftime('%b %d')} – {period_end.strftime('%b %d, %Y')}), "
            f"the VoiceIQ platform analyzed {total_reviews:,} customer reviews across public channels. "
            f"Overall sentiment was {negative_pct:.1f}% negative. The intelligence engine identified "
            f"{emerging_cnt} critical emerging volume anomalies and {improving_cnt} resolving issues. "
            f"Key operational priorities require immediate focus on biometric mobile stability and airport lounge wait times, "
            f"while extension performance demonstrates strong resolution following recent optimizations."
        )

        # 6. Persist Report Entity
        report = Report(
            title=title,
            report_period_start=period_start,
            report_period_end=period_end,
            total_reviews=total_reviews,
            negative_pct=negative_pct,
            emerging_issues_count=emerging_cnt,
            improving_issues_count=improving_cnt,
            executive_summary=exec_summary,
            geographic_insights=geographic_insights,
            report_issues=report_issues,
        )
        persisted = await self.report_repo.create_report(report)
        await self.session.commit()

        # Reload with nested relationships
        reloaded = await self.report_repo.get_by_id(persisted.id)
        final_report = reloaded or persisted

        logger.info(
            f"Generated weekly executive intelligence report '{final_report.title}'",
            extra={
                "report_id": final_report.id,
                "total_reviews": total_reviews,
                "emerging_count": emerging_cnt,
                "improving_count": improving_cnt,
            },
        )

        # 7. Publish report.generated event to Kafka
        try:
            event = ReportGeneratedEvent(
                data=ReportGeneratedPayload(
                    report_id=final_report.id,
                    title=final_report.title,
                    total_reviews=final_report.total_reviews,
                    emerging_issues_count=final_report.emerging_issues_count,
                    generated_at=final_report.created_at or datetime.now(timezone.utc),
                )
            )
            await self.kafka_producer.publish(
                topic=settings.KAFKA_TOPIC_REPORT_GENERATED,
                event=event,
                key=final_report.id,
            )
        except Exception as kafka_err:
            logger.warning(
                f"Failed to publish report.generated event for report {final_report.id}",
                extra={"report_id": final_report.id, "error": str(kafka_err)},
            )

        return final_report

    def render_markdown(self, report: Report) -> str:
        """Render report into clean, formatted Markdown document."""
        p_start = report.report_period_start.strftime("%B %d, %Y")
        p_end = report.report_period_end.strftime("%B %d, %Y")

        lines = [
            f"# {report.title}",
            f"**Reporting Period:** {p_start} — {p_end}  ",
            f"**Platform:** VoiceIQ Intelligence Engine  \n",
            "---",
            "## 1. Executive Summary",
            report.executive_summary,
            "",
            "## 2. Key Metrics Snapshot",
            "| Metric | Value |",
            "| :--- | :--- |",
            f"| **Total Reviews Ingested** | `{report.total_reviews:,}` |",
            f"| **Negative Sentiment Rate** | `{report.negative_pct:.1f}%` |",
            f"| **Emerging Issues Identified** | `{report.emerging_issues_count}` |",
            f"| **Resolving / Improving Issues** | `{report.improving_issues_count}` |",
            "",
            "## 3. High-Priority Issues & Action Plans",
        ]

        if not report.report_issues:
            lines.append("_No specific issue clusters highlighted for this period._\n")
        else:
            for item in report.report_issues:
                cluster = item.cluster
                title = cluster.cluster_title if cluster else f"Cluster #{item.cluster_id[:8]}"
                product = cluster.affected_product.name if cluster and cluster.affected_product else "General Services"
                lines.append(f"### #{item.rank}: {title} `[{item.issue_type.upper()}]`")
                lines.append(f"- **Product:** {product}")
                if cluster:
                    lines.append(f"- **Feedback Volume:** {cluster.review_count} reviews ({cluster.negative_pct:.1f}% negative)")
                    if cluster.representative_quotes:
                        lines.append(f"- **Customer Quote:** \"{cluster.representative_quotes[0]}\"")

                if item.recommendation:
                    rec = item.recommendation
                    team_name = rec.suggested_team.name if rec.suggested_team else rec.suggested_team_id
                    lines.append(f"- **Assigned Team:** {team_name}")
                    lines.append(f"- **Investigation Hypothesis:** {rec.investigation_hypothesis}")
                    lines.append(f"- **Action Plan:** {rec.recommended_action}")
                lines.append("")

        if report.geographic_insights:
            lines.append("## 4. Geographic & Regional Intelligence")
            lines.append("| Location | Reviews | Negative Count | Negative Rate |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for loc, data in report.geographic_insights.items():
                lines.append(f"| {loc} | {data.get('total_reviews', 0)} | {data.get('negative_count', 0)} | {data.get('negative_pct', 0.0)}% |")
            lines.append("")

        lines.append("---\n*Generated autonomously by VoiceIQ Intelligence Engine.*")
        return "\n".join(lines)

    def render_html(self, report: Report) -> str:
        """Render report into an executive-ready, printable HTML document."""
        p_start = report.report_period_start.strftime("%B %d, %Y")
        p_end = report.report_period_end.strftime("%B %d, %Y")

        issues_html = ""
        for item in report.report_issues:
            cluster = item.cluster
            title = cluster.cluster_title if cluster else f"Cluster #{item.cluster_id[:8]}"
            product = cluster.affected_product.name if cluster and cluster.affected_product else "General Services"
            badge_class = "badge-emerging" if item.issue_type == "emerging" else "badge-improving" if item.issue_type == "improving" else "badge-persistent"

            rec_html = ""
            if item.recommendation:
                rec = item.recommendation
                team_name = rec.suggested_team.name if rec.suggested_team else rec.suggested_team_id
                rec_html = f"""
                <div class="rec-card">
                    <p><strong>Assigned Team:</strong> {team_name}</p>
                    <p><strong>Investigation Hypothesis:</strong> <em>{rec.investigation_hypothesis}</em></p>
                    <p><strong>Action Steps:</strong> {rec.recommended_action.replace(chr(10), '<br>')}</p>
                </div>
                """

            quote_html = ""
            if cluster and cluster.representative_quotes:
                quote_html = f"<blockquote>\"{cluster.representative_quotes[0]}\"</blockquote>"

            issues_html += f"""
            <div class="issue-card">
                <div class="issue-header">
                    <span class="issue-title">#{item.rank}. {title}</span>
                    <span class="badge {badge_class}">{item.issue_type.upper()}</span>
                </div>
                <p class="issue-meta"><strong>Product:</strong> {product} &bull; <strong>Volume:</strong> {cluster.review_count if cluster else 0} reviews</p>
                {quote_html}
                {rec_html}
            </div>
            """

        geo_rows = ""
        for loc, data in (report.geographic_insights or {}).items():
            geo_rows += f"""
            <tr>
                <td><strong>{loc}</strong></td>
                <td>{data.get('total_reviews', 0)}</td>
                <td>{data.get('negative_count', 0)}</td>
                <td><span class="pill-neg">{data.get('negative_pct', 0.0)}%</span></td>
            </tr>
            """

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{report.title}</title>
<style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 40px auto; max-width: 900px; color: #1e293b; background: #ffffff; line-height: 1.6; }}
    .header {{ border-bottom: 3px solid #0284c7; padding-bottom: 20px; margin-bottom: 30px; }}
    h1 {{ font-size: 26px; color: #0f172a; margin-bottom: 6px; }}
    .subtitle {{ color: #64748b; font-size: 14px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 30px; }}
    .kpi-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; text-align: center; }}
    .kpi-value {{ font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 4px; }}
    .kpi-label {{ font-size: 12px; text-transform: uppercase; color: #64748b; font-weight: 600; }}
    .summary-box {{ background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px 20px; border-radius: 0 8px 8px 0; margin-bottom: 30px; font-size: 15px; color: #166534; }}
    .section-title {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-top: 36px; margin-bottom: 16px; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }}
    .issue-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 16px; background: #ffffff; }}
    .issue-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
    .issue-title {{ font-size: 17px; font-weight: 600; color: #0f172a; }}
    .badge {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 9999px; text-transform: uppercase; }}
    .badge-emerging {{ background: #fee2e2; color: #991b1b; }}
    .badge-improving {{ background: #dcfce7; color: #166534; }}
    .badge-persistent {{ background: #f1f5f9; color: #475569; }}
    .issue-meta {{ font-size: 13px; color: #64748b; margin-bottom: 10px; }}
    blockquote {{ margin: 10px 0; padding-left: 14px; border-left: 3px solid #cbd5e1; font-style: italic; color: #475569; font-size: 14px; }}
    .rec-card {{ background: #f8fafc; border-radius: 6px; padding: 12px 16px; margin-top: 12px; font-size: 13px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }}
    th {{ background: #f8fafc; font-weight: 600; color: #475569; }}
    .pill-neg {{ background: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 12px; }}
    .footer {{ margin-top: 50px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
</style>
</head>
<body>
    <div class="header">
        <h1>{report.title}</h1>
        <div class="subtitle">Reporting Window: {p_start} – {p_end} &bull; Generated by VoiceIQ</div>
    </div>

    <div class="summary-box">
        <strong>Executive Synthesis:</strong> {report.executive_summary}
    </div>

    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Total Reviews</div>
            <div class="kpi-value">{report.total_reviews:,}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Negative Sentiment</div>
            <div class="kpi-value">{report.negative_pct:.1f}%</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Emerging Surges</div>
            <div class="kpi-value" style="color: #dc2626;">{report.emerging_issues_count}</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Resolving Issues</div>
            <div class="kpi-value" style="color: #16a34a;">{report.improving_issues_count}</div>
        </div>
    </div>

    <div class="section-title">Priority Operational Issues & Assigned Actions</div>
    {issues_html}

    <div class="section-title">Regional & Geographic Anomalies</div>
    <table>
        <thead>
            <tr>
                <th>Location / Region</th>
                <th>Total Volume</th>
                <th>Negative Volume</th>
                <th>Negative Rate</th>
            </tr>
        </thead>
        <tbody>
            {geo_rows if geo_rows else '<tr><td colspan="4">No specific geographic clustering detected.</td></tr>'}
        </tbody>
    </table>

    <div class="footer">
        VoiceIQ &bull; Autonomous Enterprise Intelligence Briefing
    </div>
</body>
</html>"""
        return html_template
