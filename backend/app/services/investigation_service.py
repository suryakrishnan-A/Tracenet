"""Investigation Service Orchestrator.

Orchestrates evidence extraction, provider execution, validation,
uncertainty assessment, and safe error mapping.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.project import Project
from app.schemas.investigation import (
    InvestigationRequest,
    InvestigationReportResponse,
)
from app.services.issue_service import get_issue_by_id, get_recent_events_for_issue
from app.services.evidence_builder import build_evidence_package
from app.services.ai_provider import (
    get_ai_provider,
    generate_deterministic_analysis,
    AIProviderNotConfiguredError,
    AIProviderTimeoutError,
    AIProviderRateLimitError,
    AIProviderUnavailableError,
    AIMalformedResponseError,
)

logger = logging.getLogger(__name__)


async def run_issue_investigation(
    db: AsyncSession,
    project: Project,
    issue_id: uuid.UUID,
    preferences: Optional[InvestigationRequest] = None,
) -> Optional[InvestigationReportResponse]:
    """Orchestrates an investigation for an authorized issue within project scope."""
    # 1. Retrieve authorized issue
    issue = await get_issue_by_id(db, project.id, issue_id)
    if not issue:
        return None

    # 2. Retrieve recent associated telemetry events (strictly project-scoped)
    recent_events = await get_recent_events_for_issue(
        db, project.id, issue_id, limit=settings.AI_MAX_EVENTS_PER_INVESTIGATION
    )

    now = datetime.now(timezone.utc)
    provider_name = settings.AI_PROVIDER or "openai_compatible"
    model_name = settings.AI_MODEL or "gpt-4o-mini"

    # 3. Handle insufficient evidence scenario
    if not recent_events:
        return InvestigationReportResponse(
            status="insufficient_evidence",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["No telemetry events found for this issue cluster."],
            error_detail="Cannot conduct investigation because zero telemetry events are associated with this issue.",
        )

    # 4. Construct bounded, sanitized evidence package
    evidence = build_evidence_package(issue, recent_events)

    # 5. Check if AI API key is configured
    is_mock = provider_name.lower() == "mock"
    is_configured = is_mock or bool(settings.AI_API_KEY and settings.AI_API_KEY.strip())

    if not is_configured:
        # Return clear not_configured status with deterministic analysis
        deterministic_report = generate_deterministic_analysis(evidence)
        return InvestigationReportResponse(
            status="not_configured",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider="deterministic_rule_engine",
            model="heuristic-fallback-v1",
            is_ai_generated=False,
            report=deterministic_report,
            warnings=[
                "AI_API_KEY is not configured in backend environment. Generated evidence analysis using local deterministic heuristics."
            ],
            error_detail="AI provider requires AI_API_KEY in backend/.env to generate LLM-synthesized reports.",
        )

    # 6. Execute AI Provider with safe error boundaries
    provider = get_ai_provider()
    try:
        report = await provider.generate_report(evidence, preferences)
        return InvestigationReportResponse(
            status="success",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=True,
            report=report,
            warnings=[],
            error_detail=None,
        )

    except AIProviderNotConfiguredError as exc:
        return InvestigationReportResponse(
            status="not_configured",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=generate_deterministic_analysis(evidence),
            warnings=[str(exc)],
            error_detail="AI_API_KEY not configured.",
        )

    except AIProviderTimeoutError as exc:
        logger.warning(f"Investigation timeout for issue {issue_id}: {exc}")
        return InvestigationReportResponse(
            status="error",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["Provider timed out."],
            error_detail="AI Provider request timed out. Please retry in a few moments.",
        )

    except AIProviderRateLimitError as exc:
        logger.warning(f"Rate limit for issue {issue_id}: {exc}")
        return InvestigationReportResponse(
            status="error",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["Provider rate limited."],
            error_detail="AI Provider rate limit reached. Please wait before retrying.",
        )

    except AIMalformedResponseError as exc:
        logger.error(f"Malformed AI response for issue {issue_id}: {exc}")
        return InvestigationReportResponse(
            status="error",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["Received invalid format from model."],
            error_detail="The AI provider returned a malformed or non-compliant report.",
        )

    except AIProviderUnavailableError as exc:
        logger.warning(f"AI Provider unavailable for issue {issue_id}: {exc}")
        return InvestigationReportResponse(
            status="error",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["Provider connection failed."],
            error_detail="Could not reach the AI provider service. Please check provider status or network connectivity.",
        )

    except Exception as exc:
        logger.exception(f"Unexpected error during investigation for issue {issue_id}: {exc}")
        return InvestigationReportResponse(
            status="error",
            issue_id=issue.id,
            project_id=project.id,
            generated_at=now,
            provider=provider_name,
            model=model_name,
            is_ai_generated=False,
            report=None,
            warnings=["Internal failure."],
            error_detail="An unexpected internal error occurred during incident analysis.",
        )
