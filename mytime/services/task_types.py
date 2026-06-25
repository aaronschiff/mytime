from sqlalchemy import select
from sqlalchemy.orm import Session

from mytime.models import TaskType


def list_task_types(session: Session, include_inactive: bool = False) -> list[TaskType]:
    stmt = select(TaskType)
    if not include_inactive:
        stmt = stmt.where(TaskType.active.is_(True))
    stmt = stmt.order_by(TaskType.sort_order, TaskType.name)
    return list(session.scalars(stmt))


def add_task_type(session: Session, name: str) -> TaskType:
    t = TaskType(name=name.strip())
    session.add(t)
    session.commit()
    return t


def rename_task_type(session: Session, task_type_id: int, name: str) -> TaskType | None:
    t = session.get(TaskType, task_type_id)
    if t is None:
        return None
    t.name = name.strip()
    session.commit()
    return t


def set_active(session: Session, task_type_id: int, active: bool) -> TaskType | None:
    t = session.get(TaskType, task_type_id)
    if t is None:
        return None
    t.active = active
    session.commit()
    return t
