"""
A "smoke test" for the web layer (the FastAPI endpoints).

This does NOT re-check the parsing/flow logic — test_checkin.py already does
that. Its one job is to prove the HTTP wiring works: the server starts, the
endpoints respond, and the webhook reads the SAME field names Twilio will send
('From' and 'Body'). That's the exact seam where real texts could break later,
so we pin it down now.

TestClient runs the real app in-process (no network, no real server). Thanks to
conftest.py it uses a throwaway database, and we swap send_sms for a recorder.
"""

import pytest
from fastapi.testclient import TestClient

from app import flow
from app.main import app

TEST_PHONE = "+15550000000"  # matches the seeded recipient in app/config.py


@pytest.fixture
def client(monkeypatch):
    """A test client with outgoing texts captured instead of printed. It logs in
    by default (auth set) so the protected dashboard endpoints are reachable."""
    sent = []
    monkeypatch.setattr(flow, "send_sms", lambda to, body: sent.append((to, body)))
    # The 'with' block triggers the app's startup (create tables, seed people).
    with TestClient(app) as c:
        c.auth = ("family", "test-password")  # matches conftest.py
        c.sent = sent  # stash captured messages on the client for convenience
        yield c


def test_api_status_responds(client):
    resp = client.get("/api/status")
    assert resp.status_code == 200
    assert "Test (me)" in resp.json()["recipients"]


def test_dashboard_page_renders(client):
    """The family dashboard '/' returns an HTML page mentioning the recipient."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Family Check-In" in resp.text
    assert "Test (me)" in resp.text


def test_today_partial_renders(client):
    """The htmx auto-refresh endpoint returns an HTML fragment."""
    resp = client.get("/partials/today")
    assert resp.status_code == 200
    assert "Test (me)" in resp.text


def test_webhook_uses_twilio_field_names(client):
    """The whole loop over HTTP: start, then reply using Twilio's From/Body."""
    client.post("/send-checkin")

    # Twilio posts form fields literally named 'From' and 'Body'.
    r1 = client.post("/sms-webhook", data={"From": TEST_PHONE, "Body": "3"})
    assert r1.status_code == 200
    r2 = client.post("/sms-webhook", data={"From": TEST_PHONE, "Body": "yes"})
    r3 = client.post("/sms-webhook", data={"From": TEST_PHONE, "Body": "yes"})
    assert "COMPLETE" in r3.json()["result"]

    # The JSON status endpoint now shows a completed check-in with our answers.
    checkins = client.get("/api/status").json()["checkins"]
    assert len(checkins) == 1
    assert checkins[0]["feeling"] == 3
    assert checkins[0]["status"] == "complete"


def test_webhook_missing_fields_is_rejected(client):
    """Leaving out Body should be a clean 422 error, not a crash."""
    resp = client.post("/sms-webhook", data={"From": TEST_PHONE})
    assert resp.status_code == 422


def test_dashboard_requires_login(client):
    """The private pages must reject visitors who don't log in (401), and the
    webhook must stay OPEN so Twilio can still deliver replies."""
    # No credentials -> the protected pages are blocked.
    no_login = TestClient(app)
    assert no_login.get("/").status_code == 401
    assert no_login.get("/partials/today").status_code == 401
    assert no_login.get("/api/status").status_code == 401

    # Wrong password is also blocked.
    no_login.auth = ("family", "wrong-password")
    assert no_login.get("/").status_code == 401

    # But the webhook needs no login (Twilio can't log in).
    assert no_login.post("/sms-webhook", data={"From": TEST_PHONE, "Body": "3"}).status_code == 200
