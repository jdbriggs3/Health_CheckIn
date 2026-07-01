# Daily Check-In Project — Kickoff Brief

A starting context document for building a daily check-in tool for aging parents.
Paste this into a new Claude project (and/or keep it in the repo) so any session
starts with the full picture.

---

## The idea (in plain terms)

A daily check-in tool for my dad and his wife, ages 90 and 85, who live on their
own about six hours away (in Boise) and both have concerning health conditions.
They don't have internet but do use their cell phones, so the tool works through
**text messages (SMS)** — no app to install, no internet needed.

Each morning it sends a short, friendly sequence of questions:
- How are you feeling today? (scale of 1–5)
- Have you taken your morning meds? (yes/no)
- Have you eaten? (yes/no)

Their replies are saved so the tool can track them over time and alert the family
if a response is missing or their numbers start to drop.

## The most important design principle

They are sharp and fully capable — this is NOT about babysitting them. The tool
must feel **respectful and welcome**: a quick way to stay connected with family,
not something that makes them feel monitored or patronized. If it feels like
surveillance, they won't use it. Usability and dignity come first.

## Safety framing (important)

Build this as a **family information system, not a medical device.** It records
observations, organizes information, and highlights trends to support family
decisions. It should NOT try to diagnose conditions, detect medical emergencies,
or give medical advice. Keep that boundary clear in everything it does.

---

## The two halves (they fit together)

1. **Daily SMS check-in (start here):** THEY reply from their phones each day.
   Captures daily signals directly from them, no internet required.
2. **Family dashboard (later):** WE (the family) see the history and trends —
   the daily check-ins plus any visit notes. This is the web page part.

Build half 1 first as the simplest thing that works. Add half 2 once that's solid.

---

## How this maps to skills I already have (UW Python 330 course)

- **FastAPI** (Week 4) — the backend server. Sends the daily messages and
  receives the replies. Same framework used in the Photo Journal final project.
- **APIs** (Weeks 4 & 6) — the tool calls an external SMS service's API to send
  texts, and receives incoming texts via a webhook (an API endpoint on my server).
- **Databases** (SQLite/SQLAlchemy, and TinyDB from Photo Journal) — store each
  day's replies (date, 1–5 number, meds Y/N, eaten Y/N) so trends can be tracked.
- **Cloud / serverless deployment** (Weeks 7 & 8) — the app must run somewhere
  always-on (not my laptop) to text them every morning. Serverless may fit well
  and stay cheap, since it only "wakes up" to send or handle a message.
- **Full-stack web (Jinja2, TailwindCSS, htmx)** (Weeks 1–2, 5, Photo Journal) —
  for the family dashboard half, when I get there.

The one new thing not covered in the course: any AI/LLM features (e.g.
auto-summarizing visit notes) — a natural next step, not needed for version 1.

---

## Decisions still to make (rough out before building)

- **SMS service:** Twilio is the standard choice. Need to check current pricing
  before committing — expected to be very cheap at this scale (a few messages/day
  to two people), roughly a few dollars/month plus a small per-message cost.
- **Hosting:** NOT Heroku (no longer cheap). Look at current low-cost / free-tier
  options together (e.g. Render, Railway, Fly.io, PythonAnywhere, or a serverless
  option) — verify current terms before choosing.
- **Who gets alerts**, and the **timing rules** (e.g. "send the questions at 9am;
  flag the family if no reply by 11am").
- **Boise setup:** very light on their end — no app to install. Mostly: confirm
  their phones send/receive texts reliably, save the sending number so it isn't
  mistaken for spam, and do a friendly test run with them. Someone in Boise can
  help with this.

---

## Suggested first version (smallest thing that actually works)

1. A FastAPI app with two endpoints:
   - one that sends the morning question sequence (triggered on a schedule)
   - one webhook that receives their replies and saves them
2. A simple database table of daily check-ins.
3. A basic alert (e.g. email or text to me) if no reply by a set time.
4. Deployed somewhere always-on, cheaply.

Get THAT working end to end with my own phone as a test before involving them.
Then refine wording, timing, and add the family dashboard.

---

## Working setup

- **Claude project (claude.ai):** home base for planning, notes, decisions, and
  this brief. Has shared memory across chats in the project.
- **Claude Code in PyCharm:** where the actual code is written and run, directly
  in the repo on my Mac (Apple Silicon). Big step up from copy-pasting snippets.
- I work in PyCharm, use GitHub for version control (prefer the PyCharm GUI for
  git), and test in Safari.
