"""
Settings you'll actually want to change, all in one place.

For version 1 everything lives here in plain Python. Later we can move secrets
(like a real Twilio key) into environment variables — but not yet.
"""

# --- Who gets the daily check-in -------------------------------------------
# Start with ONLY your own phone so you can test the whole thing safely.
# Add your dad and his wife here later, once it feels good.
# Use full numbers in E.164 format: "+1" then the 10 digits, no spaces/dashes.
RECIPIENTS = [
    {"name": "Test (me)", "phone": "+15550000000"},
]

# Where "no reply yet" alerts go (you, the family). Same phone format.
FAMILY_ALERT_PHONE = "+15550000000"


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