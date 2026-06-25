from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from mytime.db import get_session
from mytime.services import budget, projects, settings_service
from mytime.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def overview(request: Request, session: Session = Depends(get_session)):
    summaries = [budget.project_summary(session, p)
                 for p in projects.list_projects(session, status="active")]
    return templates.TemplateResponse(request, "overview.html", {
        "summaries": summaries,
        "currency": settings_service.get_settings(session).currency_symbol,
    })
