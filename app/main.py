"""
The web server (FastAPI). It exposes the family dashboard (a web page) plus the
endpoints that drive the SMS check-in.

Endpoints:
    GET  /               -> the family dashboard (HTML web page)
    GET  /partials/today -> just the "today" panel (htmx auto-refresh)
    GET  /api/status     -> the same data as JSON (handy for testing/debugging)
    POST /send-checkin   -> send this morning's first question to everyone
    POST /sms-webhook    -> receive a reply (Twilio will call this for real later)
    POST /check-alerts   -> text the family about anyone who hasn't finished
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app import config
from app.dashboard import get_overview
from app.database import SessionLocal, init_db
from app.flow import check_missing_replies, handle_reply, start_checkins
from app.models import DailyCheckIn, Recipient
from sqlalchemy import select

# Where the HTML templates live. We build the path from THIS file's location so
# it works no matter which folder the server is started from.
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Runs once when the server boots (before 'yield') and, if we needed it,
    on shutdown (after 'yield'). This is FastAPI's current way to do startup
    work — here: create tables and seed recipients."""
    init_db()
    _seed_recipients()
    yield


app = FastAPI(title="Daily Check-In", lifespan=lifespan)


def _seed_recipients() -> None:
    """Add recipients from config.py the first time, so the DB isn't empty."""
    with SessionLocal() as session:
        for entry in config.RECIPIENTS:
            exists = session.scalar(
                select(Recipient).where(Recipient.phone == entry["phone"])
            )
            if not exists:
                session.add(Recipient(name=entry["name"], phone=entry["phone"]))
        session.commit()


@app.get("/")
def dashboard(request: Request):
    """The family dashboard: recent history and today's status, as a web page."""
    with SessionLocal() as session:
        overview = get_overview(session)
    # Jinja2Templates needs the request object; the rest is our data.
    return templates.TemplateResponse(
        request, "dashboard.html",
        {"people": overview["people"], "days": overview["days"]},
    )


@app.get("/partials/today")
def today_panel(request: Request):
    """Just the 'today at a glance' panel — htmx fetches this to auto-refresh."""
    with SessionLocal() as session:
        overview = get_overview(session)
    return templates.TemplateResponse(
        request, "_today.html", {"people": overview["people"]},
    )


@app.get("/api/status")
def api_status():
    """The raw data as JSON. Handy for testing and for any future tooling."""
    with SessionLocal() as session:
        checkins = session.scalars(select(DailyCheckIn)).all()
        return {
            "recipients": [r.name for r in session.scalars(select(Recipient)).all()],
            "checkins": [
                {
                    "recipient_id": c.recipient_id,
                    "date": str(c.date),
                    "feeling": c.feeling,
                    "meds": c.meds,
                    "eaten": c.eaten,
                    "status": c.status,
                }
                for c in checkins
            ],
        }


@app.post("/send-checkin")
def send_checkin():
    """Start the morning sequence for everyone (later: triggered on a schedule)."""
    with SessionLocal() as session:
        notes = start_checkins(session)
    return {"sent": notes}


@app.post("/sms-webhook")
def sms_webhook(
    from_phone: str = Form(..., alias="From"),
    body: str = Form(..., alias="Body"),
):
    """
    Receive an incoming text. Twilio sends form fields named 'From' and 'Body',
    so we match that shape via the field aliases — real texts will 'just work' later.
    """
    with SessionLocal() as session:
        note = handle_reply(session, from_phone=from_phone, body=body)
    return JSONResponse({"result": note})


@app.post("/check-alerts")
def check_alerts():
    """Notify the family about anyone who hasn't completed today's check-in."""
    with SessionLocal() as session:
        notes = check_missing_replies(session)
    return {"alerts": notes}
