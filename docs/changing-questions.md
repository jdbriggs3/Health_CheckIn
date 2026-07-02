# How to change or add a check-in question

The daily questions are driven by the `QUESTIONS` list in **`app/config.py`**.
Each question is a small dictionary:

```python
{
    "key": "feeling",        # short internal name
    "column": "feeling",     # which column on the daily_checkins table stores the answer
    "type": "scale_1_5",     # how to read the reply: "scale_1_5" or "yes_no"
    "prompt": "Good morning! ...",  # the exact words texted to them
}
```

The important idea: the database stores each answer in a **column named for what
it means** (`feeling`, `meds`, `eaten`), *not* for the words of the question. So
changing the wording never touches the database.

---

## Free changes (no database work) — just edit `app/config.py`

| I want to... | What to do |
|---|---|
| **Reword a question** | Change its `prompt` text. That's it. |
| **Reorder the questions** | Move the items in the `QUESTIONS` list; they're asked in list order. |
| **Remove a question** | Delete its item from `QUESTIONS`. The old column can stay unused (harmless). |
| **Change a scale/type** | Edit `type` (and the `prompt` to match). Keep it `scale_1_5` or `yes_no` unless we add a new answer type in `app/flow.py`. |

After any of these, run the tests to confirm nothing broke:

```bash
pytest
```

---

## Adding a brand-new question (this one touches the database)

Because each answer has its own column, a **new** question needs a **new column**
on the `daily_checkins` table. That table-shape change is called a *migration*.

### Step 1 — Add the column in `app/models.py`

In the `DailyCheckIn` class, add a field next to `feeling` / `meds` / `eaten`.
Use the type that matches the answer:

```python
# a 1-5 number:
sleep: Mapped[int | None] = mapped_column(Integer, nullable=True)

# a yes/no:
pain: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
```

### Step 2 — Add the question in `app/config.py`

Add an item to `QUESTIONS`, with `column` matching the field name from Step 1:

```python
{
    "key": "sleep",
    "column": "sleep",
    "type": "scale_1_5",
    "prompt": "One more: how did you sleep last night, 1 to 5?",
},
```

### Step 3 — Update the existing database

Pick the situation you're in:

- **Still testing, no real data yet:** easiest path — just delete the database
  file and let it rebuild fresh on the next start:
  ```bash
  rm checkins.db
  ```

- **There's real data you must keep:** add the column in place with SQLite's
  `ALTER TABLE` (this keeps all existing rows; the new column starts empty):
  ```bash
  sqlite3 checkins.db "ALTER TABLE daily_checkins ADD COLUMN sleep INTEGER;"
  # for a yes/no question, use BOOLEAN instead of INTEGER
  ```

> If migrations ever become frequent, the standard tool for managing them is
> **Alembic**. It's overkill for occasional changes like this, so we're not
> using it yet.

### Step 4 — Update the status view and tests

- In `app/main.py`, the `/` status endpoint lists the answers — add the new field
  there if you want to see it.
- Add a line for the new answer in `tests/test_checkin.py` (the
  `test_full_checkin_flow` test walks through every question), then run `pytest`.

---

## A note on where the *dashboard* fits

When the family dashboard (half 2) exists, a new column also becomes a new thing
to show there. That's another reason adding a question is a deliberate little
project rather than a one-line edit — but it's a well-worn path, and small.
