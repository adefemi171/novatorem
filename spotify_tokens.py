"""Durable storage and expiry metadata for Spotify refresh tokens."""

from calendar import monthrange
from datetime import datetime, timezone
import json
import os

import requests


TOKEN_KEY = "novatorem:spotify:authorization"


class TokenStoreError(RuntimeError):
    pass


def utc_now():
    return datetime.now(timezone.utc)


def isoformat(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse_datetime(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
        timezone.utc
    )


def add_months(value, months):
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class SpotifyTokenStore:
    """Uses Upstash/Vercel KV in production and an env token as a fallback."""

    def __init__(self):
        self.url = (
            os.getenv("TOKEN_STORE_REST_URL")
            or os.getenv("KV_REST_API_URL")
            or os.getenv("UPSTASH_REDIS_REST_URL")
        )
        self.token = (
            os.getenv("TOKEN_STORE_REST_TOKEN")
            or os.getenv("KV_REST_API_TOKEN")
            or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        )

    @property
    def writable(self):
        return bool(self.url and self.token)

    def _command(self, command):
        if not self.writable:
            raise TokenStoreError("Durable token storage is not configured.")

        response = requests.post(
            self.url.rstrip("/"),
            headers={"Authorization": f"Bearer {self.token}"},
            json=command,
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            raise TokenStoreError(payload["error"])
        return payload.get("result")

    def load(self):
        if self.writable:
            raw = self._command(["GET", TOKEN_KEY])
            if raw:
                return json.loads(raw)

        refresh_token = os.getenv("SPOTIFY_REFRESH_TOKEN")
        if not refresh_token:
            return None

        authorized_at = os.getenv("SPOTIFY_AUTHORIZED_AT")
        expires_at = None
        if authorized_at:
            expires_at = isoformat(add_months(parse_datetime(authorized_at), 6))

        return {
            "refresh_token": refresh_token,
            "authorized_at": authorized_at,
            "expires_at": expires_at,
            "source": "environment",
        }

    def save_authorization(self, refresh_token, authorized_at=None):
        authorized_at = authorized_at or utc_now()
        record = {
            "refresh_token": refresh_token,
            "authorized_at": isoformat(authorized_at),
            "expires_at": isoformat(add_months(authorized_at, 6)),
            "source": "durable_store",
        }
        self._command(["SET", TOKEN_KEY, json.dumps(record)])
        return record

    def rotate_refresh_token(self, refresh_token):
        record = self.load() or {}
        record["refresh_token"] = refresh_token
        record["source"] = "durable_store"
        self._command(["SET", TOKEN_KEY, json.dumps(record)])
        return record

    def status(self):
        record = self.load()
        if not record:
            return {
                "connected": False,
                "needs_reconnect": True,
                "reason": "missing_token",
                "storage_configured": self.writable,
            }

        expires_at = parse_datetime(record.get("expires_at"))
        days_remaining = None
        needs_reconnect = False
        if expires_at:
            remaining = expires_at - utc_now()
            days_remaining = max(0, int(remaining.total_seconds() // 86400))
            needs_reconnect = remaining.total_seconds() <= 0

        return {
            "connected": True,
            "needs_reconnect": needs_reconnect,
            "authorized_at": record.get("authorized_at"),
            "expires_at": record.get("expires_at"),
            "days_remaining": days_remaining,
            "storage_configured": self.writable,
            "source": record.get("source", "durable_store"),
        }

