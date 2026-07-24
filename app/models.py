"""
The shape of our data — what a "recipient" and a "daily check-in" look like.

We use SQLAlchemy, which lets us describe database tables as Python classes.
Each class = one table; each attribute = one column.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared parent for all our table classes (SQLAlchemy needs this)."""
    pass


class Recipient(Base):
    """A person who receives the daily check-in (e.g. Dad, or you for testing)."""
    __tablename__ = "recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Lets us write recipient.checkins to get all of this person's daily rows.
    checkins: Mapped[list["DailyCheckIn"]] = relationship(back_populates="recipient")


class DailyCheckIn(Base):
    """
    One row per person per day. It holds both the ANSWERS and the PROGRESS
    through the guided sequence, so we always know which question is next.
    """
    __tablename__ = "daily_checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("recipients.id"))
    date: Mapped[date] = mapped_column(Date)

    # The answers. Start empty (None) and fill in as replies come back.
    feeling: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meds: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    eaten: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # An optional free-text note in their own words ("toe hurts", "great day").
    # Blank when they don't add anything. The app only stores and displays this;
    # it never interprets it or treats it as a medical alert.
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Progress tracking for the guided sequence:
    # current_index = which question in config.QUESTIONS we're waiting on.
    # status = "in_progress" while asking, "complete" once all are answered.
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    recipient: Mapped["Recipient"] = relationship(back_populates="checkins")