"""
The database connection. We use SQLite — a whole database in a single file
(checkins.db) that appears in your project folder. No server to install.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# The file that holds all the data. Deleting it resets everything.
# We read it from an environment variable so tests (and later, a cloud host)
# can point at a different database without editing code. If the variable
# isn't set, we fall back to the normal local file.
DATABASE_URL = os.environ.get("CHECKIN_DB_URL", "sqlite:///checkins.db")

# check_same_thread=False is needed because FastAPI may touch the database
# from different threads. It's the standard setting for SQLite + FastAPI.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# A "session" is one conversation with the database (read some rows, save some
# rows, done). SessionLocal() hands us a fresh one whenever we need it.
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    """Create the tables if they don't exist yet. Safe to run every startup."""
    Base.metadata.create_all(engine)