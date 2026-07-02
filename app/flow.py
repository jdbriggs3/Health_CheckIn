"""
The conversation engine: start a check-in, and handle each reply that comes back.

This is where the "guided sequence" lives — ask one question, wait, read the
answer, then ask the next. The state (which question is next) is stored on the
DailyCheckIn row, so the app can be restarted anytime without losing its place.
"""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import DailyCheckIn, Recipient
from app.sms import send_sms


# --- Reading a person's reply ----------------------------------------------
# Casual, human wording — people won't reply in perfect "yes/no".
_YES_WORDS = {"yes", "y", "yeah", "yep", "yup", "sure", "ok", "okay", "done", "did"}
_NO_WORDS = {"no", "n", "nope", "nah", "not yet", "notyet", "havent", "haven't"}


def parse_answer(qtype: str, text: str):
    """
    Turn a raw text reply into a clean value, or None if we can't understand it.
    Returning None tells the caller to send a gentle "try again" nudge.
    """
    cleaned = text.strip().lower()

    if qtype == "scale_1_5":
        # Look for a digit 1-5 anywhere in the reply ("feeling like a 4 today").
        for char in cleaned:
            if char in "12345":
                return int(char)
        return None

    if qtype == "yes_no":
        if cleaned in _YES_WORDS:
            return True
        if cleaned in _NO_WORDS:
            return False
        # Fall back to checking the first word ("yes thanks", "no not yet").
        first = cleaned.split()[0] if cleaned.split() else ""
        if first in _YES_WORDS:
            return True
        if first in _NO_WORDS:
            return False
        return None

    return None


# --- Starting the morning check-in -----------------------------------------

def start_checkins(session: Session) -> list[str]:
    """
    Kick off today's check-in for every active recipient: create their row for
    today (if not already there) and send the first question.
    Returns a list of human-readable notes about what happened.
    """
    today = date.today()
    notes = []

    recipients = session.scalars(
        select(Recipient).where(Recipient.active == True)  # noqa: E712
    ).all()

    for person in recipients:
        existing = session.scalar(
            select(DailyCheckIn).where(
                DailyCheckIn.recipient_id == person.id,
                DailyCheckIn.date == today,
            )
        )
        if existing:
            notes.append(f"{person.name}: already started today, skipping.")
            continue

        checkin = DailyCheckIn(recipient_id=person.id, date=today, current_index=0,
                               status="in_progress")
        session.add(checkin)
        session.commit()

        first_question = config.QUESTIONS[0]
        send_sms(person.phone, first_question["prompt"])
        notes.append(f"{person.name}: sent question 1.")

    return notes


# --- Handling each reply ----------------------------------------------------

def handle_reply(session: Session, from_phone: str, body: str) -> str:
    """
    Process one incoming text. Figure out who it's from and which question
    they're answering, save the answer, then ask the next one (or wrap up).
    Returns a note describing what happened (handy while testing).
    """
    person = session.scalar(select(Recipient).where(Recipient.phone == from_phone))
    if person is None:
        return f"Ignored: no recipient with phone {from_phone}."

    today = date.today()
    checkin = session.scalar(
        select(DailyCheckIn).where(
            DailyCheckIn.recipient_id == person.id,
            DailyCheckIn.date == today,
            DailyCheckIn.status == "in_progress",
        )
    )
    if checkin is None:
        # A reply with no active check-in (already done, or before we asked).
        return f"{person.name}: reply received but no check-in in progress."

    question = config.QUESTIONS[checkin.current_index]
    value = parse_answer(question["type"], body)

    if value is None:
        # Didn't understand — nudge gently and stay on the same question.
        send_sms(person.phone, config.RETRY_MESSAGE[question["type"]])
        return f"{person.name}: couldn't parse '{body}' for {question['key']}; re-asked."

    # Save the answer onto the matching column, then advance.
    setattr(checkin, question["column"], value)
    checkin.current_index += 1

    if checkin.current_index >= len(config.QUESTIONS):
        # All done for today.
        checkin.status = "complete"
        checkin.completed_at = datetime.now()
        session.commit()
        send_sms(person.phone, config.CLOSING_MESSAGE)
        return f"{person.name}: saved {question['key']}={value}; check-in COMPLETE."

    # More questions to go — ask the next one.
    session.commit()
    next_question = config.QUESTIONS[checkin.current_index]
    send_sms(person.phone, next_question["prompt"])
    return f"{person.name}: saved {question['key']}={value}; sent next question."


# --- Alerts -----------------------------------------------------------------

def check_missing_replies(session: Session) -> list[str]:
    """
    Find active recipients who haven't COMPLETED today's check-in, and text the
    family alert phone. This is a family heads-up, not a medical alarm.
    """
    today = date.today()
    notes = []

    recipients = session.scalars(
        select(Recipient).where(Recipient.active == True)  # noqa: E712
    ).all()

    for person in recipients:
        checkin = session.scalar(
            select(DailyCheckIn).where(
                DailyCheckIn.recipient_id == person.id,
                DailyCheckIn.date == today,
            )
        )
        if checkin is None or checkin.status != "complete":
            state = "hasn't replied yet" if checkin is None else "started but not finished"
            send_sms(
                config.FAMILY_ALERT_PHONE,
                f"Heads-up: {person.name} {state} today. Might be worth a quick call.",
            )
            notes.append(f"{person.name}: alert sent ({state}).")
        else:
            notes.append(f"{person.name}: all good, checked in.")

    return notes