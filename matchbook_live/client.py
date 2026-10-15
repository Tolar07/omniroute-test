"""
Matchbook REST client — the only module that talks to the exchange.

Endpoints used (developers.matchbook.com, checked 2026-10-14):
  POST   /bpapi/rest/security/session          login -> session-token (~6 h)
  GET    /edge/rest/events                     events, markets, runners, prices
  GET    /edge/rest/account/balance            balance, exposure, free-funds
  POST   /edge/rest/v2/offers                  submit back offers
  GET    /edge/rest/v2/offers/{id}             one unsettled offer
  DELETE /edge/rest/v2/offers/{id}             cancel what is unmatched
  GET    /edge/rest/reports/v2/bets/settled    settled bets, net of commission

No deposit, withdrawal, transfer or account-settings endpoint is called, and
tests/test_live.py fails if one is added.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests

from matchbook_live import config as C

HEADERS = {"User-Agent": "olp-xdv-matchbook/1.0", "Accept": "application/json",
           "Content-Type": "application/json"}


class MatchbookError(RuntimeError):
    pass


class Client:
    def __init__(self, state_dir: Path = C.STATE_DIR, username: str = C.USERNAME,
                 password: str = C.PASSWORD, http: Optional[requests.Session] = None):
        self.state_dir = state_dir
        self.username, self.password = username, password
        self.http = http or requests.Session()
        self.token: Optional[str] = None

    # ------------------------------------------------------------ session
    def _token_file(self) -> Path:
        return self.state_dir / "session.json"

    def login(self, force: bool = False) -> str:
        """Reuse a session younger than SESSION_MAX_AGE_H; otherwise log in."""
        f = self._token_file()
        if not force and f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            age = datetime.now(timezone.utc) - datetime.fromisoformat(d["ts"])
            if age < timedelta(hours=C.SESSION_MAX_AGE_H):
                self.token = d["token"]
                return self.token
        if not (self.username and self.password):
            raise MatchbookError("MATCHBOOK_USERNAME / MATCHBOOK_PASSWORD not set")
        r = self.http.post(C.API_URL + C.LOGIN_PATH, headers=HEADERS, timeout=30,
                           json={"username": self.username, "password": self.password})
        if r.status_code != 200:
            raise MatchbookError(f"login failed: HTTP {r.status_code} {r.text[:300]}")   # body never echoes the password
        self.token = r.json()["session-token"]
        self.state_dir.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"token": self.token,
                                 "ts": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
        return self.token

    def _call(self, method: str, path: str, *, params=None, body=None, auth=True, retry=True):
        h = dict(HEADERS)
        if auth:
            h["session-token"] = self.token or self.login()
        r = self.http.request(method, C.API_URL + path, params=params, json=body, headers=h, timeout=30)
        if r.status_code == 401 and auth and retry:
            self.login(force=True)
            return self._call(method, path, params=params, body=body, auth=auth, retry=False)
        if r.status_code >= 400:
            raise MatchbookError(f"{method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json() if r.content else {}

    # ------------------------------------------------------------ read
    def events(self, offset: int = 0, per_page: int = C.PER_PAGE) -> dict:
        return self._call("GET", "/edge/rest/events", auth=False, params={
            "sport-ids": C.SPORT_IDS, "states": "open", "include-prices": "true",
            "price-depth": 3, "price-mode": "expanded", "odds-type": "DECIMAL",
            "exchange-type": "back-lay", "currency": "GBP",
            "offset": offset, "per-page": per_page})

    def balance(self) -> dict:
        return self._call("GET", "/edge/rest/account/balance")

    def offer(self, offer_id) -> dict:
        return self._call("GET", f"/edge/rest/v2/offers/{offer_id}")

    def settled(self, market_ids: list) -> list[dict]:
        out, offset = [], 0
        while True:
            d = self._call("GET", "/edge/rest/reports/v2/bets/settled", params={
                "market-ids": ",".join(str(m) for m in market_ids), "offset": offset, "per-page": 50})
            out += d.get("markets", [])
            offset += 50
            if offset >= int(d.get("total") or 0):
                return out
            time.sleep(C.PAGE_SLEEP_S)

    # ------------------------------------------------------------ write
    def back(self, runner_id, odds: float, stake: float) -> dict:
        d = self._call("POST", "/edge/rest/v2/offers", body={
            "odds-type": "DECIMAL", "exchange-type": "back-lay",
            "offers": [{"runner-id": runner_id, "side": "back", "odds": odds,
                        "stake": round(stake, 2), "keep-in-play": False}]})
        offers = d.get("offers") or []
        if not offers:
            raise MatchbookError(f"submit returned no offer: {str(d)[:300]}")
        return offers[0]

    def cancel(self, offer_id) -> dict:
        return self._call("DELETE", f"/edge/rest/v2/offers/{offer_id}")
