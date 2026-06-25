from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="mytime/templates")


def register_filters() -> None:
    """Wire format filters. Called from main after format.py exists."""
    from mytime import format as fmt
    templates.env.filters["hm"] = fmt.fmt_hm
    templates.env.filters["hms"] = fmt.fmt_hms
    templates.env.filters["money"] = fmt.money
