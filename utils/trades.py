"""Shared trade-table logic used by both the journal and the analytics pages.

Keeping one implementation guarantees that the journal total, every card and
the analytics numbers always agree.
"""

import pandas as pd

from utils.dates import parse_date_series
from utils.formulas import calculate_net_pnl, to_float

START_ROW_MARK = "Start Row"
SYNC_TOLERANCE = 0.005  # differences below half a cent are not worth a DB write
SYNC_BATCH_LIMIT = 50  # max rows written per page load


def split_trades(df):
  """Return (main_trades, subs_map) for a trades DataFrame.

  main_trades: one row per trade (the "Start Row"), newest first.
  subs_map:    {trade_id: DataFrame of all rows that belong to the trade}.
  """
  if df is None or df.empty:
    return pd.DataFrame(), {}

  if "Entry Date" in df.columns:
    order = parse_date_series(df["Entry Date"])
    df = df.assign(_order=order).sort_values("_order", ascending=False).drop(columns="_order")

  main_trades = df[df["ActionType"].astype(str).str.contains(START_ROW_MARK, case=False, na=False)]
  if main_trades.empty:
    main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

  subs_map = {pid: group for pid, group in df.groupby("Parent Trade ID", sort=False)}
  return main_trades, subs_map


def compute_pnl_map(main_trades, subs_map):
  """{trade_id: Net P/L}. Falls back to the stored value when it can't be calculated
  (e.g. the trade has no exit yet)."""
  pnl_map = {}
  if main_trades is None or main_trades.empty:
    return pnl_map
  empty = main_trades.iloc[0:0]
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    pnl = calculate_net_pnl(trade, subs_map.get(trade_id, empty))
    if pnl is None:
      pnl = to_float(trade.get("Net P/L"))
    pnl_map[trade_id] = pnl
  return pnl_map


def stale_net_pnl(main_trades, subs_map, already_tried=()):
  """Trades whose stored `Net P/L` differs from the freshly calculated value.

  Returns a list of (trade_id, new_value). Values that were already attempted in
  this session (`already_tried` holds (trade_id, str(value))) are skipped so a
  write that silently fails can't loop forever.
  """
  stale = []
  if main_trades is None or main_trades.empty:
    return stale
  empty = main_trades.iloc[0:0]
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    net = calculate_net_pnl(trade, subs_map.get(trade_id, empty))
    if net is None:
      continue
    stored = trade.get("Net P/L")
    stored_value = to_float(stored, default=None) if stored not in (None, "") else None
    if stored_value is not None and abs(stored_value - net) < SYNC_TOLERANCE:
      continue
    if (trade_id, str(net)) in already_tried:
      continue
    stale.append((trade_id, net))
  return stale[:SYNC_BATCH_LIMIT]
