"""
A simple family login for the dashboard.

The dashboard shows private health observations about two real people, so it
must NOT be open to the public (see CLAUDE.md). We protect the viewing pages
with one shared family username + password using HTTP Basic Auth: the browser
shows a small login box and remembers it for the session — no login web page to
build, and nothing new for anyone to learn.

The password lives in your .env (DASHBOARD_PASSWORD), never in the code.

To protect an endpoint, add this to its route:  dependencies=[Depends(require_login)]
"""

import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# auto_error=True means: if the browser sends no login, FastAPI automatically
# returns 401 with the header that makes the browser show its login box.
_basic = HTTPBasic()


def require_login(credentials: HTTPBasicCredentials = Depends(_basic)) -> str:
    """A guard for protected pages. Lets the request through only if the
    username and password match what's set in .env; otherwise raises 401."""
    expected_user = os.environ.get("DASHBOARD_USERNAME", "family")
    expected_password = os.environ.get("DASHBOARD_PASSWORD")

    # Refuse to serve rather than silently leave the dashboard unprotected if
    # no password has been configured. This fails safe.
    if not expected_password:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dashboard password is not set. Add DASHBOARD_PASSWORD to your .env.",
        )

    # compare_digest checks both values in constant time, so a wrong password
    # can't be guessed by timing how long the check takes.
    user_ok = secrets.compare_digest(credentials.username, expected_user)
    pass_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized.",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
