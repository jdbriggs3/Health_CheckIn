# Daily Check-In Project — Kickoff Brief

A starting context document for building a daily check-in tool for aging parents.
Paste this into a new Claude project (and/or keep it in the repo) so any session
starts with the full picture.

---

## The idea (in plain terms)

A daily check-in tool for my dad and his wife, ages 90 and 85, who live on their
own about six hours away (in Boise) and both have concerning health conditions.
They don't have internet but do use their iPhones, so the tool works through
**messages** — no app to install, nothing new to learn. (Originally planned as
SMS via Twilio; now sent as **iMessage** from a Mac at home. See "Decisions
made" below.)

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
   **Requirement: the dashboard must require a family login before real data
   goes live.** (It holds personal health observations about two people, so it
   cannot be publicly accessible.)

Build half 1 first as the simplest thing that works. Add half 2 once that's solid.

---

## How this maps to skills I already have (UW Python 330 course)

- **FastAPI** (Week 4) — the backend server. Sends the daily messages and
  receives the replies. Same framework used in the Photo Journal final project.
- **APIs** (Weeks 4 & 6) — originally: call an SMS service's API and receive
  replies on a webhook. As built: the Mac's own Messages app is the "service" —
  AppleScript to send, and reading Apple's message database to receive. Same
  shape (talk to something outside your program, handle what comes back),
  different doorway.
- **Databases** (SQLite/SQLAlchemy, and TinyDB from Photo Journal) — store each
  day's replies (date, 1–5 number, meds Y/N, eaten Y/N) so trends can be tracked.
- **Always-on deployment** (Weeks 7 & 8) — the app must run somewhere that stays
  on (not my laptop) to message them every morning. The cloud/serverless options
  from the course don't apply now that it needs a signed-in Mac, so the same
  ideas land on a **Mac mini at home** with a `launchd` background service
  instead: something that starts on its own, keeps running, and wakes on a
  schedule.
- **Full-stack web (Jinja2, TailwindCSS, htmx)** (Weeks 1–2, 5, Photo Journal) —
  for the family dashboard half, when I get there.

The one new thing not covered in the course: any AI/LLM features (e.g.
auto-summarizing visit notes) — a natural next step, not needed for version 1.

---

## Decisions made (updated 2026-09-10)

- **Messaging: iMessage, not Twilio.** Twilio was abandoned in July 2026 — the
  toll-free verification kept getting rejected and A2P registration was far too
  heavy for a two-person family tool. Everyone involved has an iPhone, so the
  messages are sent and read through the **macOS Messages app** instead. Free,
  and it arrives in the thread they already have. Sending uses AppleScript;
  receiving reads Apple's `chat.db` read-only.
- **Hosting: a Mac mini at home in Wenatchee**, not a cloud host. iMessage needs
  a real signed-in Mac, so the cloud options (Railway, Render, Fly) no longer
  apply. Acquired September 2026; setup in progress.
- **Sending identity: her own Apple ID**, so the check-in arrives from *her*, in
  the thread her dad already has, rather than from an unknown sender.
- **Who receives it, and how to stop:** the list lives in the git-ignored `.env`,
  never in this public repo. Removing someone stops their messages but keeps
  every past check-in — because the reasons someone stops are usually opting out
  or dying, and neither is a reason to erase their history.

## Decisions still to make

- **Timing rules** — e.g. "send the questions at 9am Mountain; flag the family
  if no reply by 11am." Note their timezone is Boise (Mountain), not the Mac's.
- **Who gets alerts** besides her.
- **Boise setup:** very light on their end — no app to install. Mostly: confirm
  their phones send/receive reliably, make sure her contact is saved so the
  messages look like they come from family, and do a friendly test run with
  them. Someone in Boise can help with this.
- **Backup** — once the mini holds the only real copy of the data.
- **Remote access** — reaching the dashboard from away from home, via a private
  network like Tailscale rather than opening the house to the internet.

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
