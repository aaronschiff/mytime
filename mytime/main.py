from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mytime.db import init_db
from mytime.templating import register_filters


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="mytime", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="mytime/static"), name="static")

register_filters()


from mytime.routers import settings as settings_router
from mytime.routers import projects as projects_router
from mytime.routers import time_entries as time_router
from mytime.routers import today as today_router
from mytime.routers import overview as overview_router
from mytime.routers import invoices as invoices_router
from mytime.routers import clients as clients_router

app.include_router(overview_router.router)
app.include_router(settings_router.router)
app.include_router(projects_router.router)
app.include_router(time_router.router)
app.include_router(today_router.router)
app.include_router(invoices_router.router)
app.include_router(clients_router.router)
