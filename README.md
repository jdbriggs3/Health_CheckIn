# Daily Check-In

A gentle daily check-in for aging parents, over plain **text messages (SMS)** —
no app to install, no internet needed on their end. Each morning it texts a
short, friendly sequence of questions, saves the replies, and can alert the
family if someone hasn't checked in.

> **What this is — and isn't.** This is a **family information system, not a
> medical device.** It records observations and highlights trends to support
> family decisions. It does not diagnose, detect emergencies, or give medical
> advice. And it's built to feel *respectful* — a quick way to stay connected,
> not surveillance.

The full background and plan live in [`CLAUDE.md`](CLAUDE.md).

---

## Where the project is right now

**Version 1 works end to end, locally, with fake ("console") text messages** —
so the whole loop can be built and tested with no Twilio account, no cost, and
no phones involved.

- ✅ The morning question sequence (feeling 1–5, meds yes/no, eaten yes/no)
- ✅ Reads replies (understands casual wording like "feeling like a 4" or "yep")
- ✅ Saves each day's answers to a database
- ✅ A basic "no reply yet" family alert
- ✅ A **family dashboard** web page (recent history + "today at a glance")
- ✅ Automated tests (`pytest`)
- ⏳ Not yet: real Twilio texts, always-on hosting, alert timing rules

---

## How the pieces fit together

```
app/
  config.py     # settings you'll edit: recipients, the 3 questions, wording
  models.py     # the shape of the data (a recipient; a daily check-in)
  database.py   # the SQLite database connection (data lives in checkins.db)
  sms.py        # send_sms(): fake/console now, swap in Twilio later
  flow.py       # the guided-sequence brain: ask -> read reply -> next -> alerts
  dashboard.py  # gathers the history/summary the dashboard page shows
  main.py       # the FastAPI web server and its endpoints
templates/      # the dashboard web page (Jinja2 + Tailwind + htmx)
scripts/
  seed_sample_data.py     # fill the local db with sample data to preview the dashboard
tests/          # automated tests (see "Running the tests" below)
docs/
  index.html              # PUBLIC web page (served by GitHub Pages) — see below
  changing-questions.md   # how to reword / add / remove a question
```

### The public web page (Twilio verification)

`docs/index.html` is a **public** page served by **GitHub Pages** at
<https://jdbriggs3.github.io/Health_CheckIn/>. It exists so Twilio's toll-free
SMS verification has a real, always-on URL describing the messaging program
(what it is, how people opt in, sample messages, STOP/HELP, privacy, contact).

- **It is public** — never put phone numbers, health data, or the recipients'
  names on it. It only describes the program.
- **Editing it = editing a live page.** Pages redeploys from the `dev` branch
  `/docs` folder on every push, so a change goes live about a minute after you
  push.
- **Keep it matched to the Twilio form.** Twilio rejection reason *30445* is a
  consistency check: the business name (`Health Check-In` / Deborah Briggs) and
  email (`jdbriggs3@gmail.com`) on the form must match what the page shows.

### The endpoints (URLs the app responds to)

| Method & path | What it does |
|---|---|
| `GET /` | The **family dashboard** web page |
| `GET /partials/today` | Just the "today at a glance" panel (htmx auto-refresh) |
| `GET /api/status` | The raw data as JSON (handy for testing/debugging) |
| `POST /send-checkin` | Send this morning's first question to everyone |
| `POST /sms-webhook` | Receive a reply (Twilio will call this for real later) |
| `POST /check-alerts` | Text the family about anyone who hasn't finished |

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

- Open **http://127.0.0.1:8000/** to see the **family dashboard**.
- Open **http://127.0.0.1:8000/docs** for a clickable control panel — press
  "Try it out" → "Execute" on any endpoint (no command line needed).

To preview the dashboard with a couple of weeks of realistic-looking history,
load some sample data first (safe — it only touches your local `checkins.db`):

```bash
.venv/bin/python scripts/seed_sample_data.py
```

Because texts are "fake" for now, sent messages **print in the terminal** where
the server is running. The data is stored in a file called `checkins.db` in the
project folder — delete that file anytime to start fresh.

> Tip: `--reload` makes the server restart automatically when you edit a file,
> which is handy while developing.

---

## Running the tests

```bash
pytest
```

This runs everything in the `tests/` folder in about a second and confirms the
logic and the web endpoints still work. The tests use their own throwaway
database and never touch your real `checkins.db` or send real texts. In PyCharm
you can also click the green ▶ arrows next to each test.

---

## Common tasks

- **Change or add a question:** see [`docs/changing-questions.md`](docs/changing-questions.md).
- **Add recipients:** edit `RECIPIENTS` in `app/config.py` (keep real phone
  numbers out of git — that's a to-do for when real Twilio is wired up).

---

## What's next

1. ✅ ~~The family dashboard~~ — done (recent history + "today at a glance").
2. **Real Twilio + hosting** — send actual texts from an always-on, low-cost host.
   *In progress:* toll-free number verification (required before Twilio will send
   real texts). The public page it needs is live — see "The public web page" above.
3. **Alert timing rules** — e.g. ask at 9am, alert the family if not done by 11am.

Done:

- ✅ **Feeling-trend graphs** on the dashboard — small inline SVG sparklines
  (no libraries), one per person. A richer interactive version (Chart.js via
  CDN) is a possible future upgrade.

The plan is to test real texts with **your own phone first**, and only add your
dad's and his wife's numbers once that's solid.
