# Daily Check-In

A gentle daily check-in for aging parents, sent as **iMessages** from a Mac that
stays switched on. Nothing to install on their end — the questions arrive in the
Messages app they already use, and they just reply.

> **What this is — and isn't.** This is a **family information system, not a
> medical device.** It records observations and highlights trends to support
> family decisions. It does not diagnose, detect emergencies, or give medical
> advice. And it's built to feel *respectful* — a quick way to stay connected,
> not surveillance.

The full background and plan live in [`CLAUDE.md`](CLAUDE.md).

---

## Where the project is right now

**The whole loop works, on real phones.** A message goes out from the Mac, the
reply comes back, gets understood, and lands in the database.

- ✅ The morning question sequence (feeling 1–5, meds, eaten, optional note)
- ✅ **Sending** real iMessages through the macOS Messages app
- ✅ **Reading** replies back out of Messages, understanding casual wording
  like "feeling like a 4" or "yep"
- ✅ Saves each day's answers; never processes the same reply twice
- ✅ A **family dashboard** web page, behind a family login
- ✅ Feeling-trend graphs (small inline SVG sparklines)
- ✅ A basic "no reply yet" family alert
- ✅ Automated tests (`pytest`) — 41 of them
- ⏳ Not yet: running automatically each morning, and living on the always-on
  Mac mini rather than the laptop

### Why iMessage, and not Twilio

The project originally aimed at Twilio. That was abandoned in July 2026: the
toll-free verification kept being rejected, and the A2P registration paperwork
was far too heavy for a tool that texts two family members. Everyone involved
has an iPhone, so the Messages app on a Mac does the same job for free.

The Twilio code is still in `app/sms.py` behind a switch, unused. It costs
nothing to leave there and documents the road not taken.

---

## How the pieces fit together

```
app/
  config.py     # the questions and wording; reads WHO from .env
  models.py     # the shape of the data (a recipient; a daily check-in)
  database.py   # the SQLite connection (data lives in checkins.db)
  sms.py        # SENDING: fake / imessage / twilio, chosen in .env
  receiver.py   # RECEIVING: reads new replies out of the Messages database
  flow.py       # the guided-sequence brain: ask -> read reply -> next -> alerts
  auth.py       # the family login that protects the dashboard
  dashboard.py  # gathers the history/summary the dashboard page shows
  main.py       # the FastAPI web server and its endpoints
templates/      # the dashboard web page (Jinja2 + Tailwind + htmx)
scripts/
  seed_sample_data.py   # fill the local db with sample data to preview the dashboard
tests/          # automated tests (see "Running the tests")
docs/
  index.html            # PUBLIC web page — see below
  changing-questions.md # how to reword / add / remove a question
```

### How sending and receiving actually work

**Sending** asks the Messages app to send, using a small AppleScript
(`app/sms.py:51`). macOS asks permission the first time — a one-off "allow this
to control Messages" popup.

**Receiving** has no webhook. Messages keeps every message in a SQLite file at
`~/Library/Messages/chat.db`, and `app/receiver.py` reads new incoming ones from
the phone numbers we care about. Three safety properties matter:

- It opens that file **read-only** — it physically cannot alter your messages.
- It only ever looks at the **recipients' phone numbers**, nothing else.
- It records how far it has read in `receiver_state.json`, so a reply is never
  handled twice, and the first run imports **none** of your message history.

Reading that file requires granting **Full Disk Access** to whatever launches
the app. macOS permissions are per-machine, so this must be granted again on
each Mac.

### The public web page

`docs/index.html` is a **public** page served by GitHub Pages at
<https://jdbriggs3.github.io/Health_CheckIn/>. It was built to satisfy Twilio's
toll-free verification, which no longer applies — so it is now **left over**, and
worth deciding whether to retire.

While it exists: **it is public.** Never put phone numbers, names, or health
data on it. It only describes the program.

### The endpoints (URLs the app responds to)

| Method & path | What it does |
|---|---|
| `GET /` | The **family dashboard** web page — login required |
| `GET /partials/today` | Just the "today at a glance" panel (htmx auto-refresh) — login required |
| `GET /api/status` | The raw data as JSON — login required |
| `POST /send-checkin` | Send this morning's first question to everyone active |
| `POST /sms-webhook` | Feed in a reply by hand. Left from the Twilio design; handy for testing, since real replies now arrive via `app/receiver.py` |
| `POST /check-alerts` | Text the family about anyone who hasn't finished |

---

## Who gets the check-in

**The people are private, so they live in `.env`, never in this repo** — which is
public. One line:

```
RECIPIENTS=Dad:+12085551234,Jan:+12085555678
```

Comma between people, `Name:Number` for each, numbers in full `+1` form.

- **To add someone:** add them to the line.
- **To stop someone's check-ins** — they've opted out, or they've died — remove
  them from the line.

Either way, restart the app. **Removing someone never deletes anything.** Their
messages stop, and their name and full history stay on the dashboard, marked
"no longer receiving check-ins" rather than shown as a person who didn't answer.
That behaviour is pinned down in `tests/test_recipients.py`.

**To stop every message immediately**, set `SMS_BACKEND=fake` in `.env` and
restart. Everything keeps recording; nothing goes out.

### What `.env` needs

This file is git-ignored and never leaves the machine. Create it by hand:

```
SMS_BACKEND=fake                  # fake | imessage
RECIPIENTS=Test (me):+1555...     # who gets the daily check-in
FAMILY_ALERT_PHONE=+1555...       # where "no reply yet" alerts go
DASHBOARD_USERNAME=family
DASHBOARD_PASSWORD=change-me      # the dashboard refuses to serve without this
```

`SMS_BACKEND` defaults to `fake`, so real messages can never go out by accident.

---

## Running it locally

From the project folder:

```bash
# 1. Set up (first time only): create the virtual environment and install libs
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Start the server
.venv/bin/python -m uvicorn app.main:app --reload
```

Then, in Safari:

- **http://127.0.0.1:8000/** — the family dashboard (it will ask you to log in)
- **http://127.0.0.1:8000/docs** — a clickable control panel; press "Try it out"
  → "Execute" on any endpoint, no command line needed

To preview the dashboard with a couple of weeks of realistic-looking history:

```bash
.venv/bin/python scripts/seed_sample_data.py
```

With `SMS_BACKEND=fake`, "sent" messages print in the terminal where the server
is running. The data lives in `checkins.db` — delete that file to start fresh.

---

## Running the tests

```bash
pytest
```

Runs in about a second. The tests use their own throwaway database, their own
fake `+1555` people, and never send anything — so they can't touch your real
data or message anyone by accident.

---

## Common tasks

- **Change or add a question:** see [`docs/changing-questions.md`](docs/changing-questions.md).
- **Add or remove a person:** edit `RECIPIENTS` in `.env` — see above.
- **Silence everything:** `SMS_BACKEND=fake` in `.env`, then restart.

---

## What's next

1. **Move onto the Mac mini** — the always-on machine, so it doesn't depend on a
   laptop being open. *In progress.*
2. **Run itself each morning** — a `launchd` background service that sends the
   questions and checks for replies on a schedule, in Mountain Time.
3. **Then, and only then, real people** — your dad first, on his own for a
   while, then Jan.

Before real data goes live: set a real `DASHBOARD_PASSWORD`, and clear out the
sample/test check-ins.

### Ideas, not commitments

- Recognise a texted **"STOP"** so someone can bow out themselves, without
  having to ask.
- A backup of `checkins.db`, once the mini holds the only real copy.
- Remote access to the dashboard from away from home, via a private network
  like Tailscale rather than opening the house to the internet.
