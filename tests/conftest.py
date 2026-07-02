"""
Shared test setup. pytest imports this file automatically, before your tests,
so it's the right place to make sure the app never touches your real database
during testing.

We point CHECKIN_DB_URL at a brand-new temporary file. app/database.py reads
that variable, so the whole app quietly uses the throwaway database instead of
your real checkins.db.
"""

import os
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="checkin_tests_")
os.environ["CHECKIN_DB_URL"] = f"sqlite:///{os.path.join(_tmp_dir, 'test.db')}"
