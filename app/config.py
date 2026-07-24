"""
Settings you'll actually want to change, all in one place.

Phone numbers are PRIVATE, so they do NOT live in this file (which gets uploaded
to git). Instead they're read from the git-ignored .env file. This file only ever
contains a harmless fake "+1 555..." placeholder, so your real number can never
be exposed in the shared code.
"""

import os

from dotenv import load_dotenv

# Load the private .env file so the phone numbers below are available. Safe to
# call even if there's no .env — it just does nothing.
load_dotenv()

# --- Who gets the daily check-in -------------------------------------------
# Real numbers live in .env (MY_PHONE). If it's missing we fall back to a fake
# 555 number, so this shared file never contains a real phone number.
# Use full numbers in E.164 format: "+1" then the 10 digits, no spaces/dashes.
# Add your dad and his wife here later, once it feels good.
_MY_PHONE = os.environ.get("MY_PHONE", "+15550000000")

RECIPIENTS = [
    {"name": "Test (me)", "phone": _MY_PHONE},
]

# Where "no reply yet" alerts go (you, the family). Also from .env, same fallback.
FAMILY_ALERT_PHONE = os.environ.get("FAMILY_ALERT_PHONE", _MY_PHONE)


# --- The morning questions --------------------------------------------------
# The tool asks these one at a time, waiting for a reply between each.
# "type" tells the parser how to read the answer:
#     scale_1_5 -> a number 1 through 5
#     yes_no    -> yes/no (we accept casual wording like "yep", "not yet")
# "column" is the matching field on the DailyCheckIn database row.
QUESTIONS = [
    {
        "key": "feeling",
        "column": "feeling",
        "type": "scale_1_5",
        "prompt": (
            "Good morning! \U0001F31E How are you feeling today, "
            "on a scale of 1 to 5? (5 = great, 1 = rough)"
        ),
    },
    {
        "key": "meds",
        "column": "meds",
        "type": "yes_no",
        "prompt": "Thanks! Have you taken your morning meds yet? (yes / no)",
    },
    {
        "key": "eaten",
        "column": "eaten",
        "type": "yes_no",
        "prompt": "Got it. And have you had something to eat? (yes / no)",
    },
    {
        "key": "note",
        "column": "note",
        "type": "free_text",
        # Optional, in their own words. The app only RECORDS this and shows it to
        # the family — it never interprets it or treats anything in it (like
        # "chest pain") as a medical alert. Skipping it is a perfectly fine reply.
        "prompt": (
            "Last thing — anything you'd like to add about how you're "
            "feeling? (Totally optional: a word or two, or just say \"no\".)"
        ),
    },
]

# Sent after all questions are answered. Warm, not clinical — this is the
# "stay connected with family" feeling, not a report being filed.
CLOSING_MESSAGE = (
    "That's everything — thank you! \U0001F49B "
    "So good to hear from you. Talk tomorrow."
)

# Gentle nudges if an answer doesn't parse, keyed by question type.
RETRY_MESSAGE = {
    "scale_1_5": "No rush — whenever you're ready, just reply with a number from 1 to 5.",
    "yes_no": "No worries — a simple \"yes\" or \"no\" is all I need.",
}