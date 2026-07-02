"""
Sending a text message — behind a single simple function: send_sms().

There are two "backends":

  * "fake"   (the default) — just PRINTS the message to your terminal, so you can
             build and test the whole conversation with no cost and no phones.
  * "twilio" — sends a REAL text through Twilio.

Which one is used is decided by the SMS_BACKEND setting in your .env file. It
stays on "fake" unless you deliberately set it to "twilio", so real texts can
never go out by accident. Nothing else in the app knows or cares which backend
is active — this is the only file that talks to Twilio.
"""

import os

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
    """Send a text to `to`. Uses the fake or Twilio backend per SMS_BACKEND."""
    if SMS_BACKEND == "twilio":
        _send_via_twilio(to, body)
    else:
        _send_fake(to, body)


def _send_fake(to: str, body: str) -> None:
    """Pretend to send a text. For now, show it in the terminal."""
    print(f"\n\U0001F4E4  SMS to {to}:\n    {body}\n")


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
