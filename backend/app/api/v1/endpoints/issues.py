"""Issues API Endpoints."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_project
from app.db.session import get_db
from app.models.project import Project
from app.schemas.issue import (
    IssueGroupRead,
    IssueDetailResponse,
    IssueStatusUpdate,
    IssueListResponse,
    TelemetryEventRead,
)
from app.schemas.investigation import (
    InvestigationRequest,
    InvestigationReportResponse,
)
from app.services.issue_service import (
    list_issues,
    get_issue_by_id,
    get_recent_events_for_issue,
    update_issue_status,
)
from app.services.investigation_service import run_issue_investigation

router = APIRouter()



@router.get(
    "",
    response_model=IssueListResponse,
    summary="List Project Issues",
    description="List grouped issues for the authenticated project with filtering and pagination.",
)
async def get_project_issues(
    status: Optional[str] = Query(default=None, description="Filter by status: unresolved, investigating, resolved, ignored"),
    severity: Optional[str] = Query(default=None, description="Filter by severity: info, warning, error, critical"),
    search: Optional[str] = Query(default=None, description="Search term for title or fingerprint"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page (max 100)"),
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IssueListResponse:
    """Retrieve paginated issue groups filtered by status, severity, or search text."""
    items, total = await list_issues(
        db=db,
        project_id=project.id,
        status=status,
        severity=severity,
        search=search,
        page=page,
        per_page=per_page,
    )
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return IssueListResponse(
        items=[IssueGroupRead.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


@router.get(
    "/{issue_id}",
    response_model=IssueDetailResponse,
    summary="Get Issue Details",
    description="Get details for a specific issue group along with recent associated telemetry events.",
)
async def get_issue_details(
    issue_id: uuid.UUID,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IssueDetailResponse:
    """Retrieve issue details and up to 10 most recent error occurrences."""
    issue = await get_issue_by_id(db, project.id, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID {issue_id} not found in this project.",
        )

    recent_events = await get_recent_events_for_issue(db, project.id, issue_id, limit=10)

    return IssueDetailResponse(
        issue=IssueGroupRead.model_validate(issue),
        recent_events=[TelemetryEventRead.model_validate(ev) for ev in recent_events],
    )


@router.patch(
    "/{issue_id}",
    response_model=IssueGroupRead,
    summary="Update Issue Status",
    description="Update investigation status of an issue group (unresolved, investigating, resolved, ignored).",
)
async def patch_issue_status(
    issue_id: uuid.UUID,
    status_update: IssueStatusUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> IssueGroupRead:
    """Update issue triage status with project access enforcement."""
    updated_issue = await update_issue_status(
        db=db,
        project_id=project.id,
        issue_id=issue_id,
        new_status=status_update.status,
    )
    if not updated_issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID {issue_id} not found in this project.",
        )

    return IssueGroupRead.model_validate(updated_issue)


@router.post(
    "/{issue_id}/investigate",
    response_model=InvestigationReportResponse,
    summary="Investigate Issue with AI Assistant",
    description=(
        "Analyzes trusted incident telemetry, stack traces, and occurrence patterns "
        "for the authorized issue to generate an evidence-grounded root-cause investigation report."
    ),
)
async def investigate_issue(
    issue_id: uuid.UUID,
    preferences: Optional[InvestigationRequest] = None,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> InvestigationReportResponse:
    """Run an evidence-grounded AI investigation on an issue within the authenticated project."""
    report = await run_issue_investigation(
        db=db,
        project=project,
        issue_id=issue_id,
        preferences=preferences,
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue with ID {issue_id} not found in this project.",
        )

    return report

