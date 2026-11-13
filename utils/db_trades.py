import pandas as pd
import streamlit as st
from utils.db_core import get_data_client, _uid
from utils.db_storage import delete_screenshot

TRADES_TTL = 120
PAGE_SIZE = 1000

@st.cache_data(ttl=TRADES_TTL, show_spinner=False)
def _load_trades(uid):
  if not uid:
    return pd.DataFrame()
  client = get_data_client()
  rows, start = [], 0
  while True:
    query = (
        client.table("trades")
        .select("*")
        .eq("user_id", uid)
        .order("Entry Date", desc=True)
        .order("Trade ID")
        .range(start, start + PAGE_SIZE - 1)
    )
    response = query.execute()
    data = response.data or []
    rows.extend(data)
    if len(data) < PAGE_SIZE:
      break
    start += PAGE_SIZE
  return pd.DataFrame(rows) if rows else pd.DataFrame()

def invalidate_trades():
  _load_trades.clear()

def fetch_trades():
  try:
    uid = _uid()
    if not uid:
      return pd.DataFrame()
    return _load_trades(uid)
  except Exception as e:
    st.error(f"ბაზიდან მონაცემის წამოღების შეცდომა: {e}")
    return pd.DataFrame()

def insert_trade(trade_data):
  try:
    uid = _uid()
    if uid:
      trade_data["user_id"] = uid
    get_data_client().table("trades").insert(trade_data).execute()
    invalidate_trades()
    return True
  except Exception as e:
    st.error(f"ბაზაში ჩაწერის შეცდომა: {e}")
    return False

def update_trade(trade_id, updated_data):
  try:
    supabase = get_data_client()
    response = supabase.table("trades").update(updated_data).eq("Trade ID", trade_id).execute()
    if not response.data:
      supabase.table("trades").update(updated_data).eq("id", trade_id).execute()
    invalidate_trades()
    return True
  except Exception as e:
    st.error(f"ბაზის განახლების შეცდომა: {e}")
    return False

def update_net_pnl_batch(updates):
  done = []
  client = get_data_client()
  for trade_id, value in updates:
    try:
      client.table("trades").update({"Net P/L": str(value)}).eq("Trade ID", trade_id).execute()
      done.append((trade_id, value))
    except Exception:
      continue
  if done:
    invalidate_trades()
  return done

def delete_trade(trade_id):
  try:
    supabase = get_data_client()
    urls = []
    try:
      for col in ("Trade ID", "Parent Trade ID"):
        rows = supabase.table("trades").select("Screenshot").eq(col, trade_id).execute().data
        urls += [r.get("Screenshot") for r in (rows or [])]
    except Exception:
      urls = []
    supabase.table("trades").delete().eq("Trade ID", trade_id).execute()
    supabase.table("trades").delete().eq("Parent Trade ID", trade_id).execute()
    invalidate_trades()
    for url in set(u for u in urls if u):
      delete_screenshot(url)
    return True
  except Exception as e:
    st.error(f"ბაზიდან წაშლის შეცდომა: {e}")
    return False
