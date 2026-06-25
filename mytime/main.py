from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="mytime")
app.mount("/static", StaticFiles(directory="mytime/static"), name="static")

try:  # filters require mytime.format (added in Task 2)
    from mytime.templating import register_filters
    register_filters()
except Exception:
    pass

from mytime.db import init_db


@app.on_event("startup")
def _startup() -> None:
    init_db()


from mytime.routers import settings as settings_router
from mytime.routers import projects as projects_router
from mytime.routers import time_entries as time_router
from mytime.routers import today as today_router
from mytime.routers import overview as overview_router

app.include_router(overview_router.router)
app.include_router(settings_router.router)
app.include_router(projects_router.router)
app.include_router(time_router.router)
app.include_router(today_router.router)
