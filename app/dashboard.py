"""
Gathers the information the family dashboard shows — recent check-in history and
a simple "how's today going" summary for each person.

This is deliberately just DATA (plain dictionaries), with no HTML in it, so the
web page and the tests can both use it. Remember the framing from the project
brief: we ORGANIZE and DISPLAY observations to help the family stay connected.
We do NOT diagnose or judge — no "good/bad", no medical language.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DailyCheckIn, Recipient

# Size and margins of the little trend graph (a "sparkline"), in SVG units.
SPARK_W = 240    # overall width
SPARK_H = 48     # overall height
SPARK_PAD_L = 16  # left margin, leaves room for the "5" / "1" axis labels
SPARK_PAD_R = 8   # right margin
SPARK_PAD_T = 8   # top margin
SPARK_PAD_B = 8   # bottom margin


def build_sparkline(recent: list[dict], window_start: date, days: int) -> dict:
    """
    Turn a person's feeling scores into the numbers a tiny SVG line chart needs.

    Two deliberate choices:
      * The vertical axis is FIXED to the full 1-5 scale (5 at top, 1 at bottom)
        no matter what the data is, so trends aren't visually exaggerated.
      * A missed day (no check-in) does NOT get connected across. The line
        breaks into separate "segments", leaving a visible gap.

    Points are placed left-to-right by their actual date, so a gap of missed
    days also shows as a wider gap. Returns coordinates only — the template draws.
    """
    inner_w = SPARK_W - SPARK_PAD_L - SPARK_PAD_R
    inner_h = SPARK_H - SPARK_PAD_T - SPARK_PAD_B
    day_span = (days - 1) or 1  # avoid dividing by zero if days == 1

    top_y = SPARK_PAD_T                 # where feeling 5 sits
    bottom_y = SPARK_PAD_T + inner_h     # where feeling 1 sits

    def x_of(offset: int) -> float:
        return round(SPARK_PAD_L + (offset / day_span) * inner_w, 1)

    def y_of(feeling: int) -> float:
        # Fixed 1-5 scale, flipped so a higher score is higher on the chart.
        return round(SPARK_PAD_T + ((5 - feeling) / 4) * inner_h, 1)

    # Which day-offsets have a check-in, and what feeling (may be None if the
    # check-in is still in progress and the feeling hasn't been answered yet).
    by_offset = {}
    for entry in recent:
        offset = (entry["date"] - window_start).days
        if 0 <= offset < days:
            by_offset[offset] = entry["feeling"]

    dots = []          # days with a recorded feeling (filled points)
    segments = []      # runs of consecutive recorded days, as polyline point strings
    run = []           # the run we're currently building

    for offset in range(days):
        feeling = by_offset.get(offset)
        if offset in by_offset and feeling is not None:
            x, y = x_of(offset), y_of(feeling)
            dots.append({"x": x, "y": y, "feeling": feeling})
            run.append(f"{x},{y}")
        else:
            # No recorded feeling here -> break the line, leaving a visible gap.
            if len(run) >= 2:
                segments.append(" ".join(run))
            run = []
    if len(run) >= 2:
        segments.append(" ".join(run))

    return {
        "width": SPARK_W,
        "height": SPARK_H,
        "top_y": top_y,
        "bottom_y": bottom_y,
        "axis_x1": SPARK_PAD_L,
        "axis_x2": SPARK_W - SPARK_PAD_R,
        "label_x": SPARK_PAD_L - 4,
        "dots": dots,
        "segments": segments,
    }


def get_overview(session: Session, days: int = 14) -> dict:
    """
    Build everything the dashboard needs.

    Returns a dictionary like:
        {
            "today": date(...),
            "people": [
                {
                    "name": "Dad",
                    "checked_in_today": True,
                    "today_status": "complete" | "in_progress" | "no reply yet",
                    "recent": [ {date, feeling, meds, eaten, status}, ... ],  # oldest -> newest
                    "avg_feeling": 3.8 or None,
                    "missed_days": 2,   # days in the window with no check-in at all
                },
                ...
            ],
        }
    """
    today = date.today()
    window_start = today - timedelta(days=days - 1)

    people = []
    recipients = session.scalars(
        select(Recipient).order_by(Recipient.name)
    ).all()

    for person in recipients:
        rows = session.scalars(
            select(DailyCheckIn)
            .where(
                DailyCheckIn.recipient_id == person.id,
                DailyCheckIn.date >= window_start,
            )
            .order_by(DailyCheckIn.date)  # oldest first, nice for reading left-to-right
        ).all()

        recent = [
            {
                "date": r.date,
                "feeling": r.feeling,
                "meds": r.meds,
                "eaten": r.eaten,
                "status": r.status,
            }
            for r in rows
        ]

        today_row = next((r for r in rows if r.date == today), None)
        if today_row is None:
            today_status = "no reply yet"
        else:
            today_status = today_row.status  # "in_progress" or "complete"

        feelings = [r.feeling for r in rows if r.feeling is not None]
        avg_feeling = round(sum(feelings) / len(feelings), 1) if feelings else None

        people.append(
            {
                "name": person.name,
                "checked_in_today": today_row is not None and today_row.status == "complete",
                "today_status": today_status,
                "recent": recent,
                "avg_feeling": avg_feeling,
                "missed_days": days - len(rows),
                "sparkline": build_sparkline(recent, window_start, days),
            }
        )

    return {"today": today, "days": days, "people": people}