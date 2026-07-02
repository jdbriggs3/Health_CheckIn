"""
Fill the local database with a couple of weeks of SAMPLE check-ins, purely so
you can see what the dashboard looks like with real-feeling data.

This is a development helper — it only touches your local checkins.db (which is
gitignored). To reset to empty, just delete checkins.db.

Run it from the project folder:
    .venv/bin/python scripts/seed_sample_data.py
"""

import os
import sys
from datetime import date, datetime, timedelta

# Make sure "import app..." works when running this file directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app import config
from app.database import SessionLocal, init_db
from app.models import DailyCheckIn, Recipient

DAYS = 14

# Two made-up patterns, each a GENTLE upward trend (starts lower, drifts higher)
# with a missed day mixed in. Each list is one "feeling" score per day, oldest
# first. None = they didn't check in that day (shown as a gap on the chart).
FEELING_PATTERNS = {
    "improving_a": [2, 3, 2, 3, None, 3, 4, 3, 4, 4, 4, 5, 4, 5],
    "improving_b": [3, 3, 4, None, 3, 4, 4, 5, 4, 5, 4, 5, 5, 5],
}


def _ensure_recipients(session) -> list[Recipient]:
    """Make sure the config recipients exist, then top up to at least two
    people so the two-column layout has something to show. Returns everyone,
    so the sample data covers every recipient (no empty cards)."""
    for entry in config.RECIPIENTS:
        if not session.scalar(select(Recipient).where(Recipient.phone == entry["phone"])):
            session.add(Recipient(name=entry["name"], phone=entry["phone"]))
    session.commit()

    samples = [("Sample: Dad", "+15550000001"), ("Sample: Ruth", "+15550000002")]
    for name, phone in samples:
        people = session.scalars(select(Recipient)).all()
        if len(people) >= 2:
            break
        if not session.scalar(select(Recipient).where(Recipient.phone == phone)):
            session.add(Recipient(name=name, phone=phone))
            session.commit()

    return session.scalars(select(Recipient).order_by(Recipient.id)).all()


def main() -> None:
    init_db()
    with SessionLocal() as session:
        people = _ensure_recipients(session)
        patterns = list(FEELING_PATTERNS.values())
        today = date.today()

        for person_index, person in enumerate(people):
            feelings = patterns[person_index % len(patterns)]
            for day_offset in range(DAYS):
                day = today - timedelta(days=DAYS - 1 - day_offset)
                feeling = feelings[day_offset]

                # Skip existing rows so re-running doesn't create duplicates.
                if session.scalar(
                    select(DailyCheckIn).where(
                        DailyCheckIn.recipient_id == person.id,
                        DailyCheckIn.date == day,
                    )
                ):
                    continue

                if feeling is None:
                    continue  # a "missed" day: no row at all

                session.add(
                    DailyCheckIn(
                        recipient_id=person.id,
                        date=day,
                        feeling=feeling,
                        meds=(day_offset % 5 != 0),   # occasionally not yet
                        eaten=(day_offset % 7 != 0),
                        current_index=3,
                        status="complete",
                        completed_at=datetime.now(),
                    )
                )
        session.commit()
        print(f"Sample data ready for: {', '.join(p.name for p in people)}")
        print("Start the server and open http://127.0.0.1:8000/ to see it.")


if __name__ == "__main__":
    main()