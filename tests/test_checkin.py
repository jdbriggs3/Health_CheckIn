"""
Automated tests for the check-in logic.

WHY THIS FILE MATTERS: a test is just code that runs your other code and checks
it did the right thing. Once these exist, you can change the app and run one
command to confirm you didn't break anything — instead of manually texting
yourself every time. Run them with:  pytest    (from the project folder)

We test the real logic in flow.py WITHOUT touching your real database or sending
real texts:
  * We build a throwaway in-memory database (vanishes when the test ends).
  * We replace send_sms with a fake that just records what "would" be sent,
    so we can check the exact messages.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, dashboard, flow
from app.models import Base, DailyCheckIn, Recipient

TEST_PHONE = "+15550000000"


@pytest.fixture
def session():
    """A fresh, empty in-memory database for each test (auto-cleaned up)."""
    engine = create_engine(
        "sqlite://",  # no filename = lives in memory only
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keep one shared connection so tables persist
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)
    db = TestSession()
    # Give ourselves one recipient to work with.
    db.add(Recipient(name="Test Person", phone=TEST_PHONE))
    db.commit()
    yield db
    db.close()


@pytest.fixture
def sent(monkeypatch):
    """Capture outgoing texts instead of printing them. Returns a growing list
    of (to, body) pairs so tests can inspect what was sent."""
    messages = []
    monkeypatch.setattr(flow, "send_sms", lambda to, body: messages.append((to, body)))
    return messages


# --- Testing the reply parser (pure logic, no database needed) --------------

@pytest.mark.parametrize("text,expected", [
    ("3", 3),
    ("feeling like a 4 today", 4),
    ("5!!", 5),
    ("great", None),   # no number -> we couldn't read it
    ("9", None),        # out of the 1-5 range
])
def test_parse_scale(text, expected):
    assert flow.parse_answer("scale_1_5", text) == expected


@pytest.mark.parametrize("text,expected", [
    ("yes", True),
    ("Yep", True),
    ("no", False),
    ("not yet", False),
    ("maybe later", None),  # unclear -> ask again
])
def test_parse_yes_no(text, expected):
    assert flow.parse_answer("yes_no", text) == expected


# --- Testing the full guided conversation -----------------------------------

def test_full_checkin_flow(session, sent):
    """A complete morning: send question 1, answer all four, get the closing."""
    flow.start_checkins(session)
    # First question went out.
    assert len(sent) == 1
    assert "how are you feeling" in sent[0][1].lower()

    flow.handle_reply(session, TEST_PHONE, "4")
    flow.handle_reply(session, TEST_PHONE, "yes")
    flow.handle_reply(session, TEST_PHONE, "not yet")
    flow.handle_reply(session, TEST_PHONE, "toe hurts a little")

    # The saved row has the right answers and is marked complete.
    checkin = session.query(DailyCheckIn).one()
    assert checkin.feeling == 4
    assert checkin.meds is True
    assert checkin.eaten is False
    assert checkin.note == "toe hurts a little"
    assert checkin.status == "complete"

    # The warm closing message was the last thing sent.
    assert sent[-1][1] == config.CLOSING_MESSAGE


def test_unclear_reply_asks_again(session, sent):
    """A confusing answer should NOT advance — we re-ask the same question."""
    flow.start_checkins(session)
    sent.clear()  # ignore the first question, focus on the reply handling

    flow.handle_reply(session, TEST_PHONE, "hello there")  # not a 1-5

    checkin = session.query(DailyCheckIn).one()
    assert checkin.current_index == 0   # still on question 1
    assert checkin.feeling is None      # nothing saved
    assert len(sent) == 1               # a single gentle retry nudge


def test_reply_from_unknown_number_is_ignored(session, sent):
    """A text from a stranger shouldn't create or change anything."""
    note = flow.handle_reply(session, "+19998887777", "hi")
    assert "no recipient" in note.lower()
    assert session.query(DailyCheckIn).count() == 0
    assert sent == []


def test_alert_when_no_checkin(session, sent):
    """If someone hasn't checked in, the family alert phone gets a heads-up."""
    flow.check_missing_replies(session)
    assert len(sent) == 1
    to, body = sent[0]
    assert to == config.FAMILY_ALERT_PHONE
    assert "Test Person" in body


def test_no_alert_after_completed_checkin(session, sent):
    """Once the check-in is complete, no alert should be sent."""
    flow.start_checkins(session)
    flow.handle_reply(session, TEST_PHONE, "5")
    flow.handle_reply(session, TEST_PHONE, "yes")
    flow.handle_reply(session, TEST_PHONE, "yes")
    flow.handle_reply(session, TEST_PHONE, "no")  # declines the optional note
    sent.clear()

    flow.check_missing_replies(session)
    assert sent == []  # nothing sent = all good


# --- Testing the dashboard summary ------------------------------------------

def test_overview_summarizes_a_completed_checkin(session, sent):
    """After a full check-in, the dashboard overview reflects it correctly."""
    flow.start_checkins(session)
    flow.handle_reply(session, TEST_PHONE, "4")
    flow.handle_reply(session, TEST_PHONE, "yes")
    flow.handle_reply(session, TEST_PHONE, "no")
    flow.handle_reply(session, TEST_PHONE, "no")  # declines the optional note

    overview = dashboard.get_overview(session, days=14)
    assert overview["days"] == 14
    person = overview["people"][0]
    assert person["name"] == "Test Person"
    assert person["checked_in_today"] is True
    assert person["today_status"] == "complete"
    assert person["avg_feeling"] == 4.0
    assert person["recent"][-1]["feeling"] == 4  # newest entry


def test_overview_when_no_checkin_yet(session):
    """With no check-ins, the person shows as 'no reply yet' and no average."""
    overview = dashboard.get_overview(session, days=7)
    person = overview["people"][0]
    assert person["checked_in_today"] is False
    assert person["today_status"] == "no reply yet"
    assert person["avg_feeling"] is None
    assert person["missed_days"] == 7
    # No check-ins at all: nothing to plot and no line.
    assert person["sparkline"]["dots"] == []
    assert person["sparkline"]["segments"] == []


# --- Testing the feeling-trend sparkline ------------------------------------

def test_sparkline_axis_is_fixed_to_1_through_5():
    """A 5 sits exactly on the top axis line and a 1 on the bottom, regardless
    of the data — the vertical scale is always the full 1-5 range."""
    from datetime import date, timedelta

    window_start = date(2026, 6, 1)
    recent = [
        {"date": window_start, "feeling": 5},
        {"date": window_start + timedelta(days=1), "feeling": 1},
    ]
    spark = dashboard.build_sparkline(recent, window_start, days=5)

    dot5, dot1 = spark["dots"]
    assert dot5["y"] == spark["top_y"]      # feeling 5 -> top of the chart
    assert dot1["y"] == spark["bottom_y"]   # feeling 1 -> bottom of the chart
    assert dot1["x"] > dot5["x"]            # later day is further right


def test_sparkline_breaks_line_at_missed_days():
    """A missed day (no check-in) splits the line rather than connecting across,
    leaving a visible gap."""
    from datetime import date, timedelta

    window_start = date(2026, 6, 1)
    recent = [
        {"date": window_start, "feeling": 3},                       # day 0
        {"date": window_start + timedelta(days=1), "feeling": 4},   # day 1
        # day 2 missing
        {"date": window_start + timedelta(days=3), "feeling": 4},   # day 3
        {"date": window_start + timedelta(days=4), "feeling": 5},   # day 4
    ]
    spark = dashboard.build_sparkline(recent, window_start, days=5)

    assert len(spark["dots"]) == 4
    assert len(spark["segments"]) == 2      # line split into two runs by the gap


def test_sparkline_single_point_has_no_line():
    """A lone recorded day can't form a line segment (needs two points)."""
    from datetime import date, timedelta

    window_start = date(2026, 6, 1)
    recent = [{"date": window_start + timedelta(days=2), "feeling": 3}]
    spark = dashboard.build_sparkline(recent, window_start, days=5)

    assert len(spark["dots"]) == 1
    assert spark["segments"] == []