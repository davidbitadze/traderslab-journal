"""Parsing of manually entered trade dates.

Brokers and spreadsheets paste dates in many shapes ("Nov 10, 1:38:02 PM",
"2026-11-10 13:38:02", "10/11/2026 13:38"). Some of them have no year at all;
pandas then silently answers year 0001, which is what broke the journal.

`parse_trade_datetime` understands those shapes and always returns a naive
`pandas.Timestamp` (or `NaT`). When the year is missing it assumes the current
year (or the previous one if that would put the date in the future).
"""

import re
from datetime import date, datetime, timedelta
from functools import lru_cache

import pandas as pd
from dateutil import parser as _dateutil

DB_FORMAT = "%Y-%m-%d %H:%M:%S"
DISPLAY_FORMAT = "%d %b %Y, %H:%M"

# Years before this are treated as "no year given" (e.g. 0001 produced by old pastes).
MIN_VALID_YEAR = 1990
# A year-less date that lands further ahead than this is taken from the previous year.
FUTURE_TOLERANCE = timedelta(days=2)

_ISO_FAST = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(:\d{2})?$")
_SPACE_CHARS = dict.fromkeys(map(ord, "   ​"), " ")


def _with_year(moment, year):
  """`moment` moved to `year`; Feb 29 falls back to the nearest earlier leap year."""
  for candidate in range(year, year - 9, -1):
    try:
      return moment.replace(year=candidate)
    except ValueError:
      continue
  return None


def _assume_year(moment, today):
  """Fill in a missing year: current year, or last year if that is in the future."""
  filled = _with_year(moment, today.year)
  if filled is None:
    return None
  if filled > datetime.combine(today, datetime.min.time()) + FUTURE_TOLERANCE:
    filled = _with_year(moment, today.year - 1)
  return filled


@lru_cache(maxsize=16384)
def _parse_text(text, today):
  """Cached: the same strings are parsed again on every Streamlit rerun."""
  if _ISO_FAST.match(text):
    try:
      moment = datetime.fromisoformat(text)
    except ValueError:
      moment = None
    if moment is not None and moment.year >= MIN_VALID_YEAR:
      return moment

  try:
    first = _dateutil.parse(text, default=datetime(2000, 1, 1))
  except (ValueError, OverflowError, TypeError):
    return None

  # Parse twice with different default years: if the result follows the default,
  # the text contained no year.
  try:
    second = _dateutil.parse(text, default=datetime(2001, 1, 1))
    year_missing = first.year != second.year
  except (ValueError, OverflowError, TypeError):
    year_missing = True  # e.g. "Feb 29" is invalid in 2001

  moment = first.replace(tzinfo=None)
  if year_missing or moment.year < MIN_VALID_YEAR:
    return _assume_year(moment, today)
  return moment


def parse_trade_datetime(value, today=None):
  """Return a naive `pd.Timestamp` for `value`, or `pd.NaT` if it can't be read."""
  if value is None:
    return pd.NaT
  today = today or date.today()

  if isinstance(value, (pd.Timestamp, datetime)):
    moment = pd.Timestamp(value)
    if pd.isna(moment):
      return pd.NaT
    moment = moment.tz_localize(None) if moment.tzinfo else moment
    if moment.year < MIN_VALID_YEAR:
      fixed = _assume_year(moment.to_pydatetime(), today)
      return pd.Timestamp(fixed) if fixed else pd.NaT
    return moment

  try:
    if pd.isna(value):
      return pd.NaT
  except (TypeError, ValueError):
    pass

  text = str(value).translate(_SPACE_CHARS).strip().strip(",")
  if not text or text.lower() in ("nan", "nat", "none", "n/a"):
    return pd.NaT
  moment = _parse_text(text, today)
  return pd.Timestamp(moment) if moment is not None else pd.NaT


def parse_date_series(values):
  """Vectorised helper: Series of anything -> Series of naive Timestamps (NaT on failure)."""
  today = date.today()
  parsed = [parse_trade_datetime(v, today) for v in values]
  return pd.Series(pd.to_datetime(parsed), index=getattr(values, "index", None))


def format_db_datetime(moment):
  """Canonical string stored in the `Entry Date` column."""
  return pd.Timestamp(moment).strftime(DB_FORMAT)


def format_display_datetime(value, fallback=None):
  """Human readable date for cards; unreadable values are shown as-is."""
  moment = parse_trade_datetime(value)
  if pd.isna(moment):
    return str(value) if fallback is None else fallback
  return moment.strftime(DISPLAY_FORMAT)
