"""
A SAFE Twilio check — confirms your credentials work WITHOUT sending any text.

Run it with:   .venv/bin/python scripts/check_twilio.py

It reads your .env, connects to Twilio, and reports whether your Account SID and
Auth Token are valid and whether your "from" number is really on your account.
It never sends a message, so it's safe to run anytime — including while your
toll-free number is still waiting on verification.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

sid = os.environ.get("TWILIO_ACCOUNT_SID")
token = os.environ.get("TWILIO_AUTH_TOKEN")
from_number = os.environ.get("TWILIO_FROM_NUMBER")

if not (sid and token):
    print("❌ Missing TWILIO_ACCOUNT_SID and/or TWILIO_AUTH_TOKEN in your .env.")
    print("   Copy .env.example to .env and fill them in, then run this again.")
    sys.exit(1)

from twilio.rest import Client  # noqa: E402  (import after the checks above)
from twilio.base.exceptions import TwilioRestException  # noqa: E402

client = Client(sid, token)

try:
    account = client.api.accounts(sid).fetch()
except TwilioRestException as err:
    print("❌ Twilio rejected your credentials.")
    print(f"   Details: {err.msg}")
    print("   Double-check the Account SID and Auth Token were copied exactly.")
    sys.exit(1)

print(f"✅ Credentials work. Account: {account.friendly_name} (status: {account.status}).")

if from_number:
    owned = client.incoming_phone_numbers.list(phone_number=from_number)
    if owned:
        print(f"✅ Your from-number {from_number} is on this account.")
    else:
        print(f"⚠️  {from_number} was NOT found on this account — check TWILIO_FROM_NUMBER.")
else:
    print("ℹ️  No TWILIO_FROM_NUMBER set yet (fine for now — needed to send).")

print("\nNothing was sent. This was a read-only check.")
