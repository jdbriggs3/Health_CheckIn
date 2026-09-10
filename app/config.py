"""
Settings you'll actually want to change, all in one place.

Names and phone numbers are PRIVATE, so they do NOT live in this file (which
gets uploaded to a PUBLIC git repo). Instead they're read from the git-ignored
.env file. This file only ever contains a harmless fake "+1 555..." placeholder,
so no real person can be exposed in the shared code.
"""

import os

from dotenv import load_dotenv

# Load the private .env file so the phone numbers below are available. Safe to
# call even if there's no .env — it just does nothing.
load_dotenv()

# --- Who gets the daily check-in -------------------------------------------
# The list of people lives in .env, on ONE line, like this:
#
#     RECIPIENTS=Dad:+12085551234,Jan:+12085555678
#
# People are separated by commas; each person is "Name:Number". Use full numbers
# in E.164 format: "+1" then the 10 digits, no spaces or dashes. (A name can
# contain spaces and brackets, but not a comma.)
#
# To ADD someone, add them to that line. To STOP someone's check-ins — they've
# opted out, or they've died — remove them from the line. Either way, restart
# the app for it to take effect. Removing someone NEVER deletes their history:
# see _sync_recipients() in app/main.py.
_PLACEHOLDER_PHONE = "+15550000000"


def _parse_recipients(raw: str) -> list[dict]:
    """Turn "Dad:+1208...,Jan:+1208..." into [{"name": ..., "phone": ...}, ...].

    Splits each person at the LAST colon, so a name may itself contain a colon.
    Anything malformed (no colon, or a missing half) is skipped rather than
    crashing — a typo in .env should never stop the morning check-in entirely.
    """
    people = []
    for chunk in raw.split(","):
        name, separator, phone = chunk.strip().rpartition(":")
        if not separator:
            continue
        name, phone = name.strip(), phone.strip()
        if name and phone:
            people.append({"name": name, "phone": phone})
    return people


# Prefer the RECIPIENTS line. Fall back to the older single MY_PHONE setting so
# an existing .env keeps working, and finally to a fake number so the tests and
# the public code never touch a real person.
_MY_PHONE = os.environ.get("MY_PHONE", "").strip()
_RAW_RECIPIENTS = os.environ.get("RECIPIENTS", "").strip()

if _RAW_RECIPIENTS:
    RECIPIENTS = _parse_recipients(_RAW_RECIPIENTS)
elif _MY_PHONE:
    RECIPIENTS = [{"name": "Test (me)", "phone": _MY_PHONE}]
else:
    RECIPIENTS = [{"name": "Test (me)", "phone": _PLACEHOLDER_PHONE}]

# Where "no reply yet" alerts go (you, the family). Also from .env.
FAMILY_ALERT_PHONE = (
    os.environ.get("FAMILY_ALERT_PHONE", "").strip()
    or _MY_PHONE
    or _PLACEHOLDER_PHONE
)


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