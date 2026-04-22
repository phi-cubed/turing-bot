"""HTTP client helpers for Turing race platform.

Used by setup_gara_bot.py and avvia_gara_bot.py to drive the UI via requests.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class TuringError(RuntimeError):
    """Raised when an HTTP interaction with Turing does not behave as expected."""


@dataclass
class TuringClient:
    base_url: str
    session: requests.Session = field(default_factory=requests.Session)
    username: str | None = None
    timeout: float = 30.0

    def url(self, path: str) -> str:
        return urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        r = self.session.get(self.url(path), timeout=self.timeout, **kwargs)
        return r

    def post(self, path: str, *, data=None, files=None, referer: str | None = None,
             allow_redirects: bool = True, **kwargs: Any) -> requests.Response:
        headers = kwargs.pop("headers", {})
        if referer:
            headers.setdefault("Referer", self.url(referer))
        r = self.session.post(
            self.url(path), data=data, files=files, headers=headers,
            timeout=self.timeout, allow_redirects=allow_redirects, **kwargs)
        return r

    def get_csrf(self, path: str) -> tuple[str, BeautifulSoup]:
        """Fetch a page and extract its csrfmiddlewaretoken. Returns (token, soup)."""
        r = self.get(path)
        if r.status_code != 200:
            raise TuringError(
                f"GET {path} returned {r.status_code}: {r.text[:500]}")
        soup = BeautifulSoup(r.text, "html.parser")
        token_input = soup.find("input", attrs={"name": "csrfmiddlewaretoken"})
        if not token_input or not token_input.get("value"):
            raise TuringError(f"No csrfmiddlewaretoken found at {path}")
        return token_input["value"], soup

    def login(self, username: str, password: str) -> None:
        """Log in via /accounts/login/. Raises TuringError on failure."""
        token, _ = self.get_csrf("/accounts/login/")
        data = {
            "csrfmiddlewaretoken": token,
            "username": username,
            "password": password,
            "next": "/engine/",
        }
        r = self.post(
            "/accounts/login/", data=data, referer="/accounts/login/",
            allow_redirects=False)
        if r.status_code not in (301, 302):
            raise TuringError(
                f"Login fallito per {username}: status {r.status_code}, "
                f"body head: {r.text[:300]}")
        self.username = username

    def logout(self) -> None:
        """Log out by clearing cookies and hitting /accounts/logout/ if session exists."""
        try:
            self.session.get(self.url("/accounts/logout/"), timeout=self.timeout)
        finally:
            self.session.cookies.clear()
            self.username = None

    def ensure_admin_access(self) -> None:
        """Confirm current session can reach /admin/ (user is_staff)."""
        r = self.get("/admin/", allow_redirects=False)
        if r.status_code != 200:
            raise TuringError(
                f"L'utente {self.username!r} non ha accesso a /admin/ "
                f"(status {r.status_code}). Serve un utente con is_staff=True.")

    _ADMIN_CHANGELINK = re.compile(r"/admin/engine/user/(\d+)/change/")

    def find_user_pk(self, username: str) -> int | None:
        """Search the Django admin for a User by username; return its PK or None."""
        r = self.get(f"/admin/engine/user/?q={username}")
        if r.status_code != 200:
            raise TuringError(
                f"GET /admin/engine/user/?q={username} returned {r.status_code}")
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            m = self._ADMIN_CHANGELINK.search(a["href"])
            if not m:
                continue
            # Confirm the row's username matches exactly (search is fuzzy).
            row_text = a.get_text(strip=True)
            if row_text == username:
                return int(m.group(1))
        return None

    def create_user(self, username: str, password: str) -> int:
        """Create a User via the Django admin. Returns the new PK.

        Raises TuringError if creation fails (including duplicate username).
        """
        token, _ = self.get_csrf("/admin/engine/user/add/")
        data = {
            "csrfmiddlewaretoken": token,
            "username": username,
            "password1": password,
            "password2": password,
            "_save": "Save",
        }
        r = self.post(
            "/admin/engine/user/add/", data=data,
            referer="/admin/engine/user/add/", allow_redirects=False)
        if r.status_code not in (301, 302):
            # Django admin re-renders the form with errors on 200.
            soup = BeautifulSoup(r.text, "html.parser")
            errors = soup.find_all(class_="errorlist")
            detail = " | ".join(e.get_text(" ", strip=True) for e in errors)
            raise TuringError(
                f"Creazione utente {username!r} fallita (status {r.status_code}): "
                f"{detail or r.text[:300]}")
        pk = self.find_user_pk(username)
        if pk is None:
            raise TuringError(
                f"Utente {username!r} creato ma non trovato dopo la creazione.")
        return pk

    def reset_password(self, user_pk: int, new_password: str) -> None:
        """Reset a user's password via /admin/engine/user/<pk>/password/."""
        path = f"/admin/engine/user/{user_pk}/password/"
        token, _ = self.get_csrf(path)
        data = {
            "csrfmiddlewaretoken": token,
            "password1": new_password,
            "password2": new_password,
        }
        r = self.post(path, data=data, referer=path, allow_redirects=False)
        if r.status_code not in (301, 302):
            soup = BeautifulSoup(r.text, "html.parser")
            errors = soup.find_all(class_="errorlist")
            detail = " | ".join(e.get_text(" ", strip=True) for e in errors)
            raise TuringError(
                f"Reset password per utente {user_pk} fallito "
                f"(status {r.status_code}): {detail or r.text[:300]}")

    def ensure_user(self, username: str, password: str = None, change_create: bool = True) -> int:
        """Get-or-create a user. If exists and password is provided, resets it. Returns PK."""
        pk = self.find_user_pk(username)
        if pk is not None:
            if password and change_create:
                self.reset_password(pk, password)
            return pk
        if not password:
            raise TuringError(
                f"Utente {username!r} non esiste e non è stata fornita una password per crearlo.")
        return self.create_user(username, password)


def die(msg: str, code: int = 1) -> None:
    """Print an error message to stderr and exit."""
    print(f"[ERRORE] {msg}", file=sys.stderr)
    sys.exit(code)
