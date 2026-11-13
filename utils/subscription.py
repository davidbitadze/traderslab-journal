"""Subscription validity rules (pure functions, no Streamlit/DB access)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from dateutil import parser as _dateutil

# Statuses that grant access (the database enforces the same list).
ACCESS_STATUSES = ("active", "trial")
ALL_STATUSES = ("active", "trial", "suspended", "cancelled")


@dataclass(frozen=True)
class SubscriptionState:
  valid: bool
  reason: str  # ok | inactive | expired | bad_date
  expires_at: Optional[datetime] = None
  days_left: Optional[int] = None


def parse_expiry(value):
  """Timestamp from the database -> timezone-aware UTC datetime.

  Accepts "...Z", "...+00:00", fractional seconds, naive strings (treated as UTC)
  and datetime objects. Raises ValueError when the value can't be understood.
  """
  if value is None or value == "":
    return None
  moment = value if isinstance(value, datetime) else _dateutil.parse(str(value))
  if moment.tzinfo is None:
    moment = moment.replace(tzinfo=timezone.utc)
  return moment.astimezone(timezone.utc)


def evaluate(prefs, now=None):
  """Decide whether the user may use the app.

  Valid only if the status grants access AND the expiry (when set) is in the
  future. An unreadable expiry date fails closed (access denied).
  """
  now = now or datetime.now(timezone.utc)
  status = str((prefs or {}).get("subscription_status") or "").strip().lower()
  if status not in ACCESS_STATUSES:
    return SubscriptionState(False, "inactive")

  try:
    expires_at = parse_expiry((prefs or {}).get("subscription_expires_at"))
  except (ValueError, OverflowError, TypeError):
    return SubscriptionState(False, "bad_date")

  if expires_at is None:
    return SubscriptionState(True, "ok")
  if expires_at <= now:
    return SubscriptionState(False, "expired", expires_at, 0)
  return SubscriptionState(True, "ok", expires_at, (expires_at - now).days)
