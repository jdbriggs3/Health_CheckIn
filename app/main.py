"""
The web server (FastAPI). It exposes a few URLs ("endpoints") that make things
happen. Run it, then trigger these endpoints to drive the check-in.

Endpoints:
    GET  /              -> a quick status page (today's check-ins)
    POST /send-checkin  -> send this morning's first question to everyone
    POST /sms-webhook   -> receive a reply (Twilio will call this for real later)
    POST /check-alerts  -> text the family about anyone who hasn't finished
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse

from app import config
from app.database import SessionLocal, init_db
from app.flow import check_missing_replies, handle_reply, start_checkins
from app.models import DailyCheckIn, Recipient
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
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
def status():
    """A friendly peek at where today's check-ins stand."""
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
def sms_webhook(From: str = Form(...), Body: str = Form(...)):
    """
    Receive an incoming text. Twilio sends form fields named 'From' and 'Body',
    so we match that shape now — real texts will 'just work' later.
    """
    with SessionLocal() as session:
        note = handle_reply(session, from_phone=From, body=Body)
    return JSONResponse({"result": note})


@app.post("/check-alerts")
def check_alerts():
    """Notify the family about anyone who hasn't completed today's check-in."""
    with SessionLocal() as session:
        notes = check_missing_replies(session)
    return {"alerts": notes}