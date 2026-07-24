"""
Tests for the message-sending backends (app/sms.py).

These never send a real message. We replace subprocess.run (the thing that
actually invokes macOS) with a recorder, so we can check the app builds the
right osascript command and handles failures — safely and with no phones.
"""

import pytest

from app import sms


class _FakeCompleted:
    """Stand-in for subprocess.run's return value."""
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_imessage_backend_invokes_osascript_with_number_and_body(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(returncode=0)

    monkeypatch.setattr(sms.subprocess, "run", fake_run)

    sms._send_via_imessage("+15550000000", "Good morning! 🌞")

    assert len(calls) == 1
    cmd = calls[0]
    assert cmd[0] == "osascript"
    # The phone number and message are passed as the LAST two arguments, so no
    # amount of quotes/emoji/newlines in the message can break the command.
    assert cmd[-2] == "+15550000000"
    assert cmd[-1] == "Good morning! 🌞"


def test_imessage_backend_raises_on_failure(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeCompleted(returncode=1, stderr="Messages got an error")

    monkeypatch.setattr(sms.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="iMessage send to .* failed"):
        sms._send_via_imessage("+15550000000", "hi")


def test_send_sms_routes_to_imessage_backend(monkeypatch):
    """When SMS_BACKEND is 'imessage', send_sms() uses the iMessage sender."""
    used = []
    monkeypatch.setattr(sms, "SMS_BACKEND", "imessage")
    monkeypatch.setattr(sms, "_send_via_imessage", lambda to, body: used.append((to, body)))

    sms.send_sms("+15550000000", "hello")

    assert used == [("+15550000000", "hello")]
