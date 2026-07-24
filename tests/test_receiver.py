"""
Tests for the iMessage reader (app/receiver.py).

These do NOT touch your real Messages database. Instead they replace the one
function that reads it (new_replies_since) with a stand-in that returns canned
replies, so we can test the important part — that new replies get fed into the
app's check-in logic exactly once — safely and instantly.
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, flow, receiver
from app.models import Base, DailyCheckIn, Recipient

# The number process_new_replies() will look up — must match the app's config.
PHONE = config.RECIPIENTS[0]["phone"]


@pytest.fixture
def session():
    """A fresh in-memory database with our one recipient (auto-cleaned up)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Recipient(name="Test Person", phone=PHONE))
    db.commit()
    yield db
    db.close()


@pytest.fixture
def sent(monkeypatch):
    """Capture outgoing texts instead of printing/sending them."""
    messages = []
    monkeypatch.setattr(flow, "send_sms", lambda to, body: messages.append((to, body)))
    return messages


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    """Point the watermark file at a throwaway temp path, not the real one."""
    path = tmp_path / "receiver_state.json"
    monkeypatch.setattr(receiver, "STATE_FILE", str(path))
    return path


def _fake_reader(canned):
    """A stand-in for new_replies_since that honors the since_rowid watermark,
    just like the real one does when reading the database."""
    def fake(number, since_rowid):
        return [r for r in canned if r["rowid"] > since_rowid]
    return fake


def test_first_run_initializes_and_processes_nothing(session, sent, state_file, monkeypatch):
    """The very first run should just record a starting point — never import old
    messages — so we don't accidentally replay years of message history."""
    monkeypatch.setattr(receiver, "_current_max_rowid", lambda: 500)

    notes = receiver.process_new_replies(session)

    assert "First run" in notes[0]
    assert json.loads(state_file.read_text())["last_rowid"] == 500
    assert sent == []
    assert session.query(DailyCheckIn).count() == 0


def test_processes_new_replies_into_a_saved_checkin(session, sent, state_file, monkeypatch):
    """A full set of replies flows through handle_reply and lands in the database."""
    state_file.write_text(json.dumps({"last_rowid": 100}))  # already initialized
    flow.start_checkins(session)  # a morning check-in is in progress
    sent.clear()

    canned = [
        {"rowid": 101, "text": "4", "unix_time": 1},
        {"rowid": 102, "text": "yes", "unix_time": 2},
        {"rowid": 103, "text": "no", "unix_time": 3},
        {"rowid": 104, "text": "toe hurts", "unix_time": 4},
    ]
    monkeypatch.setattr(receiver, "new_replies_since", _fake_reader(canned))

    receiver.process_new_replies(session)

    checkin = session.query(DailyCheckIn).one()
    assert checkin.feeling == 4
    assert checkin.meds is True
    assert checkin.eaten is False
    assert checkin.note == "toe hurts"
    assert checkin.status == "complete"
    # The watermark advanced to the newest message we handled.
    assert json.loads(state_file.read_text())["last_rowid"] == 104


def test_same_reply_is_not_handled_twice(session, sent, state_file, monkeypatch):
    """Running twice must NOT reprocess a reply — the watermark prevents it."""
    state_file.write_text(json.dumps({"last_rowid": 100}))
    flow.start_checkins(session)

    canned = [{"rowid": 101, "text": "4", "unix_time": 1}]
    monkeypatch.setattr(receiver, "new_replies_since", _fake_reader(canned))

    # First pass handles the "4" (advances to question 2).
    receiver.process_new_replies(session)
    assert session.query(DailyCheckIn).one().feeling == 4
    assert session.query(DailyCheckIn).one().current_index == 1

    # Second pass: watermark is now 101, so the same "4" is skipped entirely.
    notes = receiver.process_new_replies(session)
    assert session.query(DailyCheckIn).one().current_index == 1  # unchanged
    assert "No new replies" in notes[0]