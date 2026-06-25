from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from mytime.templating import templates

app = FastAPI(title="mytime")
app.mount("/static", StaticFiles(directory="mytime/static"), name="static")

try:  # filters require mytime.format (added in Task 2)
    from mytime.templating import register_filters
    register_filters()
except Exception:
    pass


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "_placeholder.html")
