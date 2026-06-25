from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="mytime/templates")


def register_filters() -> None:
    from mytime import format as fmt
    templates.env.filters["hm"] = fmt.fmt_hm
    templates.env.filters["hms"] = fmt.fmt_hms
    templates.env.filters["money"] = fmt.money
    templates.env.filters["money_cents"] = fmt.money_cents
    templates.env.filters["truncate_words"] = fmt.truncate_words
    templates.env.filters["date"] = fmt.fmt_date
