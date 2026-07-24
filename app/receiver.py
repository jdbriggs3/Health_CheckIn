"""
Reading incoming iMessage replies from the macOS Messages app.

This is the RECEIVE half of the iMessage approach (app/sms.py is the SEND half).
The Messages app keeps every message in a SQLite database at
    ~/Library/Messages/chat.db
We only ever READ from that file — never write — and we only look at messages
from the specific phone numbers we care about. Reading it requires that whatever
runs this (PyCharm / the terminal) has macOS "Full Disk Access".

For now this module just *finds and returns* a reply so you can see it working.
Hooking it up to the app's parse/save logic (handle_reply) is the next step.
"""

import json
import os
import sqlite3

from sqlalchemy.orm import Session

from app import config
from app.flow import handle_reply

# The Messages database. expanduser turns "~" into your home folder.
CHAT_DB = os.path.expanduser("~/Library/Messages/chat.db")

# Where we remember how far we've already read, so the same reply is never
# handled twice. A small JSON file next to the app; git-ignored, safe to delete
# (deleting it just means "start watching from now" again).
STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "receiver_state.json")

# Apple stores each message's date as nanoseconds since 2001-01-01. Adding this
# many seconds converts it to a normal Unix timestamp (seconds since 1970).
_APPLE_EPOCH_OFFSET = 978307200


def _open_readonly() -> sqlite3.Connection:
    """Open the Messages database in READ-ONLY mode.

    The "mode=ro" below is a hard safety belt: this connection is physically
    unable to change or delete anything in your messages. It can only read.
    """
    return sqlite3.connect(f"file:{CHAT_DB}?mode=ro", uri=True)


def _known_outgoing_texts() -> set[str]:
    """Every message WE send — so we can ignore our own words echoed back.

    Quirk of self-testing: when you text your OWN number, each message you send
    ALSO appears as "received". Skipping any received message whose text exactly
    matches one of our own prompts leaves only genuine replies. For real
    recipients (a different phone number) nothing here matches, so it's harmless.
    """
    texts = {q["prompt"] for q in config.QUESTIONS}
    texts.add(config.CLOSING_MESSAGE)
    texts.update(config.RETRY_MESSAGE.values())
    return {t.strip() for t in texts}


def _decode_attributed_body(blob: bytes | None) -> str | None:
    """Best-effort: pull plain text out of Apple's binary 'attributedBody' field.

    Newer macOS sometimes leaves message.text empty and stores the words in this
    packed binary field instead. Fully decoding it is complex; this handles the
    common case of a short, plain text reply (which is all our check-ins are).
    Returns None if it can't confidently find readable text.
    """
    if not blob:
        return None
    try:
        # The visible text is stored as an NSString right after an "NSString"
        # marker. A 0x2b ('+') byte then signals a short string, followed by one
        # length byte and that many UTF-8 bytes.
        start = blob.find(b"NSString")
        if start == -1:
            return None
        plus = blob.find(b"\x2b", start)
        if plus == -1:
            return None
        length = blob[plus + 1]
        if length & 0x80:  # long-string encoding (rare for replies) — skip safely
            return None
        text_bytes = blob[plus + 2: plus + 2 + length]
        decoded = text_bytes.decode("utf-8", errors="replace").strip()
        return decoded or None
    except Exception:
        # Never let a weird message crash the reader — just report "couldn't read".
        return None


def _row_to_reply(row, outgoing: set[str]) -> dict | None:
    """Turn one database row into a clean reply dict, or None if it's not a
    genuine reply (unreadable, or one of our own prompts echoed back)."""
    rowid, text, attributed_body, unix_time = row
    body = text if text else _decode_attributed_body(attributed_body)
    if not body:
        return None
    if body.strip() in outgoing:
        return None  # our own question echoed back during self-testing — skip
    return {"rowid": rowid, "text": body.strip(), "unix_time": int(unix_time)}


def latest_reply(number: str) -> dict | None:
    """Return the newest genuine REPLY from `number`, or None if there isn't one.

    A "genuine reply" is an incoming message (is_from_me = 0) whose text is not
    one of our own prompts echoed back. This only looks at `number` and only
    reads — it touches nothing else in your messages.

    Returns a dict like {"rowid": 97131, "text": "Yes", "unix_time": 1753...} so
    later code can both use the text and remember which message it was.
    """
    outgoing = _known_outgoing_texts()
    conn = _open_readonly()
    try:
        rows = conn.execute(
            """
            SELECT m.ROWID, m.text, m.attributedBody,
                   m.date / 1000000000 + ? AS unix_time
            FROM message m
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE h.id = ? AND m.is_from_me = 0
            ORDER BY m.date DESC
            LIMIT 25
            """,
            (_APPLE_EPOCH_OFFSET, number),
        ).fetchall()
    finally:
        conn.close()

    for row in rows:
        reply = _row_to_reply(row, outgoing)
        if reply is not None:
            return reply
    return None


def new_replies_since(number: str, since_rowid: int) -> list[dict]:
    """All genuine replies from `number` newer than `since_rowid`, OLDEST first.

    Oldest-first matters: if someone answered several questions in a row, we want
    to feed them back in the order they were sent. Read-only, scoped to `number`.
    """
    outgoing = _known_outgoing_texts()
    conn = _open_readonly()
    try:
        rows = conn.execute(
            """
            SELECT m.ROWID, m.text, m.attributedBody,
                   m.date / 1000000000 + ? AS unix_time
            FROM message m
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE h.id = ? AND m.is_from_me = 0 AND m.ROWID > ?
            ORDER BY m.ROWID ASC
            """,
            (_APPLE_EPOCH_OFFSET, number, since_rowid),
        ).fetchall()
    finally:
        conn.close()

    replies = [_row_to_reply(row, outgoing) for row in rows]
    return [r for r in replies if r is not None]


# --- Remembering how far we've read (so we never handle a reply twice) ------

def _load_watermark() -> int | None:
    """The id of the last message we processed, or None if we've never run."""
    try:
        with open(STATE_FILE) as f:
            return json.load(f).get("last_rowid")
    except (FileNotFoundError, ValueError):
        return None


def _save_watermark(rowid: int) -> None:
    """Remember that we've now processed everything up to and including `rowid`."""
    with open(STATE_FILE, "w") as f:
        json.dump({"last_rowid": rowid}, f)


def _current_max_rowid() -> int:
    """The id of the newest message in the whole database right now."""
    conn = _open_readonly()
    try:
        row = conn.execute("SELECT MAX(ROWID) FROM message").fetchone()
    finally:
        conn.close()
    return row[0] or 0


# --- The main entry point: read new replies and feed them into the app ------

def process_new_replies(session: Session) -> list[str]:
    """Find any brand-new replies and run them through the app's check-in logic.

    This is the piece that connects the Messages database to the rest of the app.
    For each recipient it reads replies newer than the last one we handled, and
    hands each to handle_reply() — the SAME parse/save logic the tests use. It
    records the highest message id it has processed so the same reply is never
    saved twice.

    On the very FIRST run it just records "start watching from here" and processes
    nothing older, so it never re-imports your existing message history.
    Returns human-readable notes about what happened (handy while testing).
    """
    watermark = _load_watermark()
    if watermark is None:
        start = _current_max_rowid()
        _save_watermark(start)
        return [f"First run — now watching for replies newer than message #{start}."]

    notes = []
    highest = watermark
    for person in config.RECIPIENTS:
        for reply in new_replies_since(person["phone"], watermark):
            note = handle_reply(session, person["phone"], reply["text"])
            notes.append(f"[msg #{reply['rowid']}] {note}")
            highest = max(highest, reply["rowid"])

    if highest > watermark:
        _save_watermark(highest)
    if not notes:
        notes.append("No new replies since last check.")
    return notes


# Lets you try it straight from the terminal:  python -m app.receiver
if __name__ == "__main__":
    number = config.RECIPIENTS[0]["phone"]
    print(f"Looking for the newest reply from {number} ...")
    reply = latest_reply(number)
    if reply is None:
        print("  No genuine reply found (only our own messages, or none yet).")
    else:
        print(f"  Found reply (message #{reply['rowid']}): {reply['text']!r}")
