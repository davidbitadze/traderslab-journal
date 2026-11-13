import pandas as pd
import streamlit as st

# იმპორტები დამხმარე და გამოყოფილი მოდულებიდან
from utils.db_core import call_rpc, get_data_client, new_auth_client, get_supabase_client, _uid
from utils.db_storage import thumb_url, delete_screenshot, upload_screenshot

# ქეშის ვადა (წმ). ბაზაში ჩაწერისას ქეში ყოველთვის იწმინდება
TRADES_TTL = 120
SETTINGS_TTL = 600
BALANCE_TTL = 300

# Supabase ერთ მოთხოვნაზე ნაგულისხმევად მაქს. 1000 რიგს აბრუნებს
PAGE_SIZE = 1000

BALANCE_COLUMNS = ["Transaction ID", "Date", "Amount", "Description"]


# ------------------------------------------------------------------ trades
@st.cache_data(ttl=TRADES_TTL, show_spinner=False)
def _load_trades(uid):
  """ყველა რიგის წამოღება მკაცრად მიმდინარე იუზერის (uid) მიხედვით."""
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
  """არსებული გარიგების მონაცემების განახლება Trade ID-ის (ან id-ის) მიხედვით."""
  try:
    supabase = get_data_client()
    response = (
        supabase.table("trades")
        .update(updated_data)
        .eq("Trade ID", trade_id)
        .execute()
    )
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


# ---------------------------------------------------------------- settings (ახალი სვეტებით: pattern და trigger)
@st.cache_data(ttl=SETTINGS_TTL, show_spinner=False)
def _load_settings(uid, category):
  if not uid:
    return []
  client = get_data_client()
  target_col = "pattern" if category == "pattern" else "trigger"
  
  response = (
      client.table("user_settings")
      .select(f"id, {target_col}")
      .eq("user_id", uid)
      .execute()
  )
  
  items = [row[target_col] for row in (response.data or []) if row.get(target_col)]

  # თუ იუზერს ამ კატეგორიაში ჩანაწერი არ აქვს, ავტომატურად ვუწერთ საწყის 3-3 დეფოლტს
  if not items:
    defaults = (
        ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"]
        if category == "pattern"
        else ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]
    )
    for d in defaults:
      try:
        client.table("user_settings").insert({
            "category": category,
            target_col: d,
            "user_id": uid
        }).execute()
      except Exception:
        pass
    items = defaults

  return items


def fetch_settings(category):
  try:
    uid = _uid()
    if not uid:
      return []
    return _load_settings(uid, category)
  except Exception:
    return ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"] if category == "pattern" else ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]


def add_setting_item(category, item_name):
  try:
    uid = _uid()
    if not uid or not item_name.strip():
      return False
    target_col = "pattern" if category == "pattern" else "trigger"
    
    # ვწერთ ზუსტად იმ სვეტში, რომელიც გჭირდება
    get_data_client().table("user_settings").insert(
        {
            "category": category,
            target_col: item_name.strip(),
            "user_id": uid
        }
    ).execute()
    _load_settings.clear()
    return True
  except Exception as e:
    st.error(f"დამატების შეცდომა: {e}")
    return False


def delete_setting_item(category, item_name):
  try:
    uid = _uid()
    if not uid:
      return False
    target_col = "pattern" if category == "pattern" else "trigger"
    
    get_data_client().table("user_settings").delete().eq(
        "category", category
    ).eq(target_col, item_name).eq("user_id", uid).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


def update_setting_item(category, old_name, new_name):
  try:
    uid = _uid()
    if not uid or not new_name.strip():
      return False
    target_col = "pattern" if category == "pattern" else "trigger"
    
    get_data_client().table("user_settings").update(
        {target_col: new_name.strip()}
    ).eq("category", category).eq(target_col, old_name).eq("user_id", uid).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False

# ------------------------------------------------------- balance transactions
@st.cache_data(ttl=BALANCE_TTL, show_spinner=False)
def _load_balance(uid):
  if not uid:
    return pd.DataFrame(columns=BALANCE_COLUMNS)
  response = (
      get_data_client().table("balance_transactions").select("*").eq("user_id", uid).execute()
  )
  return (
      pd.DataFrame(response.data)
      if response.data
      else pd.DataFrame(columns=BALANCE_COLUMNS)
  )


def fetch_balance_transactions():
  try:
    return _load_balance(_uid())
  except Exception:
    return pd.DataFrame(columns=BALANCE_COLUMNS)


def add_balance_transaction(data):
  try:
    uid = _uid()
    if uid:
      data["user_id"] = uid
    get_data_client().table("balance_transactions").insert(data).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    st.error(f"შეცდომა ბაზაში ჩაწერისას: {e}")
    return False


def delete_balance_transaction(txn_id):
  try:
    get_data_client().table("balance_transactions").delete().eq(
        "Transaction ID", txn_id
    ).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    st.error(f"შეცდომა ტრანზაქციის წაშლისას: {e}")
    return False


# ---------------------------------------------------------- user preferences
def fetch_user_preferences(user_id):
  try:
    response = (
        get_data_client()
        .table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if response.data and len(response.data) > 0:
      return response.data[0]
    return None
  except Exception as e:
    print(f"პარამეტრების წაკითხვის შეცდომა: {e}")
    return None


def upsert_user_preferences(user_id, mobile_mode=None, desktop_mode=None):
  data = {}
  if mobile_mode is not None:
    data["mobile_view_mode"] = mobile_mode
  if desktop_mode is not None:
    data["desktop_view_mode"] = desktop_mode
  return update_user_preference_fields(user_id, **data)


EDITABLE_PREFERENCE_FIELDS = ("language", "theme", "mobile_view_mode", "desktop_view_mode")


def update_user_preference_fields(user_id, **fields):
  data = {k: v for k, v in fields.items() if k in EDITABLE_PREFERENCE_FIELDS}
  if not data:
    return True
  try:
    get_data_client().table("user_preferences").update(data).eq("user_id", user_id).execute()
    cached = st.session_state.get("user_prefs")
    if isinstance(cached, dict):
      cached.update(data)
    return True
  except Exception as e:
    st.error(f"ბაზის დეტალური შეცდომა: {e}")
    return False


# ----------------------------------------------------------------- RPC helpers
def ensure_user_preferences():
  data, error = call_rpc("ensure_my_preferences")
  if error or not isinstance(data, dict):
    return None
  return data


def fetch_my_staff_role():
  data, error = call_rpc("my_staff_role")
  if error:
    return None
  if isinstance(data, list):
    data = data[0] if data else None
  return data if data in ("admin", "mentor") else None
