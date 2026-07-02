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

from app import config, flow
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
    """A complete morning: send question 1, answer all three, get the closing."""
    flow.start_checkins(session)
    # First question went out.
    assert len(sent) == 1
    assert "how are you feeling" in sent[0][1].lower()

    flow.handle_reply(session, TEST_PHONE, "4")
    flow.handle_reply(session, TEST_PHONE, "yes")
    flow.handle_reply(session, TEST_PHONE, "not yet")

    # The saved row has the right answers and is marked complete.
    checkin = session.query(DailyCheckIn).one()
    assert checkin.feeling == 4
    assert checkin.meds is True
    assert checkin.eaten is False
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
    sent.clear()

    flow.check_missing_replies(session)
    assert sent == []  # nothing sent = all good