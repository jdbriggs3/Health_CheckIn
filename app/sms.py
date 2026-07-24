"""
Sending a message — behind a single simple function: send_sms().

There are a few "backends":

  * "fake"     (the default) — just PRINTS the message to your terminal, so you
               can build and test the whole conversation with no cost, no phones.
  * "imessage" — sends a REAL iMessage through the macOS Messages app (this is
               the approach we're using: no paid service, just your own Mac).
  * "twilio"   — sends a REAL text through Twilio (kept for reference; unused).

Which one is used is decided by the SMS_BACKEND setting in your .env file. It
stays on "fake" unless you deliberately change it, so real messages can never go
out by accident. Nothing else in the app knows or cares which backend is active
— this one file is the only place that actually sends.
"""

import os
import subprocess

from dotenv import load_dotenv

# Read the .env file (if present) into environment variables. Safe to call even
# when there's no .env — it just does nothing.
load_dotenv()

# "fake" (print to terminal) or "twilio" (send for real). Default: fake.
SMS_BACKEND = os.environ.get("SMS_BACKEND", "fake").strip().lower()

# Your Twilio credentials — only needed when SMS_BACKEND is "twilio".
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")


def send_sms(to: str, body: str) -> None:
    """Send a message to `to`. Picks the backend from SMS_BACKEND."""
    if SMS_BACKEND == "imessage":
        _send_via_imessage(to, body)
    elif SMS_BACKEND == "twilio":
        _send_via_twilio(to, body)
    else:
        _send_fake(to, body)


def _send_fake(to: str, body: str) -> None:
    """Pretend to send a text. For now, show it in the terminal."""
    print(f"\n\U0001F4E4  SMS to {to}:\n    {body}\n")


def _send_via_imessage(to: str, body: str) -> None:
    """Send a REAL iMessage by asking the macOS Messages app (via AppleScript).

    Requirements: you're signed into iMessage in the Messages app, and macOS has
    granted "Automation" permission to control Messages (a one-time popup the
    first time). We pass `to` and `body` as separate arguments to the script, so
    apostrophes, emoji, or line breaks in the message can't break anything.
    """
    applescript = (
        "on run {targetBuddy, targetMessage}\n"
        '    tell application "Messages"\n'
        "        set targetService to 1st account whose service type = iMessage\n"
        "        set theBuddy to participant targetBuddy of targetService\n"
        "        send targetMessage to theBuddy\n"
        "    end tell\n"
        "end run"
    )
    result = subprocess.run(
        ["osascript", "-e", applescript, to, body],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"iMessage send to {to} failed: "
            f"{result.stderr.strip() or 'unknown error from osascript'}"
        )
    print(f"\U0001F4E4  Sent iMessage to {to}.")


def _send_via_twilio(to: str, body: str) -> None:
    """Send a REAL text through Twilio. Only runs when SMS_BACKEND == 'twilio'."""
    missing = [
        name
        for name, value in [
            ("TWILIO_ACCOUNT_SID", TWILIO_ACCOUNT_SID),
            ("TWILIO_AUTH_TOKEN", TWILIO_AUTH_TOKEN),
            ("TWILIO_FROM_NUMBER", TWILIO_FROM_NUMBER),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(
            "SMS_BACKEND is 'twilio' but these are missing from your .env: "
            + ", ".join(missing)
        )

    # Imported here (not at the top) so the fake backend needs no Twilio library.
    from twilio.rest import Client

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    message = client.messages.create(to=to, from_=TWILIO_FROM_NUMBER, body=body)
    print(f"\U0001F4E4  Sent real SMS to {to} (Twilio id {message.sid}).")
