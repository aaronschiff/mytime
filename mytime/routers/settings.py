from decimal import Decimal

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from mytime.db import get_session
from mytime.services import settings_service, task_types
from mytime.templating import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request, "settings.html", {
        "settings": settings_service.get_settings(session),
        "task_types": task_types.list_task_types(session, include_inactive=True),
    })


@router.post("/settings")
def save_settings(
    default_hourly_rate: Decimal = Form(...),
    currency_symbol: str = Form(...),
    default_gst_rate: str = Form(""),
    session: Session = Depends(get_session),
):
    gst_rate = Decimal(default_gst_rate) if default_gst_rate.strip() else None
    settings_service.update_settings(session, default_hourly_rate, currency_symbol,
                                     default_gst_rate=gst_rate)
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/task-types")
def add_task(name: str = Form(...), session: Session = Depends(get_session)):
    task_types.add_task_type(session, name)
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/task-types/{task_type_id}/rename")
def rename_task(task_type_id: int, name: str = Form(...), session: Session = Depends(get_session)):
    task_types.rename_task_type(session, task_type_id, name)
    return RedirectResponse("/settings", status_code=303)


@router.post("/settings/task-types/{task_type_id}/active")
def toggle_task(task_type_id: int, active: int = Form(...), session: Session = Depends(get_session)):
    task_types.set_active(session, task_type_id, bool(active))
    return RedirectResponse("/settings", status_code=303)
