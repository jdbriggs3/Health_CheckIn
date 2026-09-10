"""
Tests for WHO receives the check-in, and — more importantly — who stops.

The scenario these protect is a real one, and it has to work on a day nobody
wants to be debugging software:

    start with just me -> add Dad -> add Jan -> someone opts out, or dies

Removing a person from the RECIPIENTS line in .env must genuinely stop their
daily messages, and must NEVER throw away what they already told us.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config, dashboard, main
from app.config import _parse_recipients
from app.models import Base, DailyCheckIn, Recipient

DAD = "+15550000011"
JAN = "+15550000022"


@pytest.fixture
def Session(monkeypatch):
    """A throwaway in-memory database, wired in as the one _sync_recipients uses.

    Returns the session *maker* rather than a session, so each step of a test can
    open and close its own — the same way the real app does.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # one shared connection, so the tables persist
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine)
    monkeypatch.setattr(main, "SessionLocal", maker)
    return maker


# --- Reading the RECIPIENTS line out of .env --------------------------------

def test_parse_reads_names_and_numbers():
    people = _parse_recipients(f"Dad:{DAD},Jan:{JAN}")
    assert people == [
        {"name": "Dad", "phone": DAD},
        {"name": "Jan", "phone": JAN},
    ]


def test_parse_tolerates_spaces_and_bracketed_names():
    people = _parse_recipients(f"  Test (me) : {DAD} ")
    assert people == [{"name": "Test (me)", "phone": DAD}]


def test_parse_skips_malformed_entries_instead_of_crashing():
    """A typo in .env must not be able to stop the whole morning check-in."""
    people = _parse_recipients(f"Dad:{DAD},oops-no-colon,:{JAN},Jan:")
    assert people == [{"name": "Dad", "phone": DAD}]


# --- Keeping the database in step with .env ---------------------------------

def test_sync_adds_people_listed_in_env(Session, monkeypatch):
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Dad", "phone": DAD}])
    main._sync_recipients()

    with Session() as s:
        people = s.scalars(select(Recipient)).all()
        assert [(p.name, p.phone, p.active) for p in people] == [("Dad", DAD, True)]


def test_adding_a_second_person_leaves_the_first_alone(Session, monkeypatch):
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Dad", "phone": DAD}])
    main._sync_recipients()

    monkeypatch.setattr(config, "RECIPIENTS", [
        {"name": "Dad", "phone": DAD},
        {"name": "Jan", "phone": JAN},
    ])
    main._sync_recipients()

    with Session() as s:
        active = {p.phone for p in s.scalars(select(Recipient)) if p.active}
        assert active == {DAD, JAN}


def test_removing_someone_stops_their_checkins_but_keeps_their_history(Session, monkeypatch):
    """THE important one: opting out, or dying, must not erase the record."""
    monkeypatch.setattr(config, "RECIPIENTS", [
        {"name": "Dad", "phone": DAD},
        {"name": "Jan", "phone": JAN},
    ])
    main._sync_recipients()

    # Give Dad some history worth keeping.
    with Session() as s:
        dad = s.scalar(select(Recipient).where(Recipient.phone == DAD))
        s.add(DailyCheckIn(
            recipient_id=dad.id, date=date.today() - timedelta(days=1),
            current_index=4, status="complete", feeling=4, meds=True, eaten=True,
            note="Slept well",
        ))
        s.commit()

    # Dad comes off the RECIPIENTS line in .env.
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Jan", "phone": JAN}])
    main._sync_recipients()

    with Session() as s:
        dad = s.scalar(select(Recipient).where(Recipient.phone == DAD))
        assert dad is not None, "the person must not be deleted"
        assert dad.active is False, "their check-ins must stop"
        assert dad.name == "Dad", "their name is still part of the record"

        history = s.scalars(
            select(DailyCheckIn).where(DailyCheckIn.recipient_id == dad.id)
        ).all()
        assert len(history) == 1
        assert history[0].feeling == 4
        assert history[0].note == "Slept well"

        # And the person still on the list is untouched.
        jan = s.scalar(select(Recipient).where(Recipient.phone == JAN))
        assert jan.active is True


def test_re_adding_someone_turns_their_checkins_back_on(Session, monkeypatch):
    """Someone who opted out may change their mind."""
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Dad", "phone": DAD}])
    main._sync_recipients()
    monkeypatch.setattr(config, "RECIPIENTS", [])
    main._sync_recipients()
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Dad", "phone": DAD}])
    main._sync_recipients()

    with Session() as s:
        dad = s.scalar(select(Recipient).where(Recipient.phone == DAD))
        assert dad.active is True
        # Still one row — re-adding must not create a duplicate person.
        assert len(s.scalars(select(Recipient)).all()) == 1


def test_sync_picks_up_a_corrected_name(Session, monkeypatch):
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Jann", "phone": JAN}])
    main._sync_recipients()
    monkeypatch.setattr(config, "RECIPIENTS", [{"name": "Jan", "phone": JAN}])
    main._sync_recipients()

    with Session() as s:
        assert s.scalar(select(Recipient).where(Recipient.phone == JAN)).name == "Jan"


# --- What the family sees afterwards ----------------------------------------

def test_inactive_person_is_never_shown_as_missing(Session):
    """A person no longer receiving check-ins is a record, not an open question.

    Without this, the dashboard would greet the family every morning with
    "Dad — no reply yet · missed 47 days", which is the last thing anyone needs
    to read after a death.
    """
    with Session() as s:
        s.add(Recipient(name="Dad", phone=DAD, active=False))
        s.add(Recipient(name="Jan", phone=JAN, active=True))
        s.commit()

        dad = s.scalar(select(Recipient).where(Recipient.phone == DAD))
        s.add(DailyCheckIn(
            recipient_id=dad.id, date=date.today() - timedelta(days=3),
            current_index=4, status="complete", feeling=5,
        ))
        s.commit()

        overview = dashboard.get_overview(s, days=14)

    people = {p["name"]: p for p in overview["people"]}

    assert people["Dad"]["active"] is False
    assert people["Dad"]["today_status"] == "inactive"
    assert people["Dad"]["checked_in_today"] is False
    assert people["Dad"]["missed_days"] == 0, "missed days must not pile up forever"
    assert len(people["Dad"]["recent"]) == 1, "their history is still there"

    # Someone still receiving check-ins is described the usual way.
    assert people["Jan"]["today_status"] == "no reply yet"
    assert people["Jan"]["active"] is True
