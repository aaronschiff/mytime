import pytest
from mytime.services import task_types as tt


def test_add_and_list(session):
    tt.add_task_type(session, "Analysis")
    tt.add_task_type(session, "Meetings")
    names = [t.name for t in tt.list_task_types(session)]
    assert names == ["Analysis", "Meetings"]


def test_rename(session):
    t = tt.add_task_type(session, "Anlaysis")
    tt.rename_task_type(session, t.id, "Analysis")
    assert tt.list_task_types(session)[0].name == "Analysis"


def test_retire_hides_from_default_list(session):
    t = tt.add_task_type(session, "Admin")
    tt.set_active(session, t.id, False)
    assert tt.list_task_types(session) == []
    assert len(tt.list_task_types(session, include_inactive=True)) == 1
    tt.set_active(session, t.id, True)
    assert len(tt.list_task_types(session)) == 1
