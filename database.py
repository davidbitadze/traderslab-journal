import pandas as pd
import streamlit as st

# იმპორტები ახალი გამოყოფილი მოდულებიდან
from utils.db_core import get_data_client, new_auth_client, get_supabase_client, _uid
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


def delete_trade(trade_id):
  """გარიგების და მასთან დაკავშირებული ქვემოქმედებების წაშლა Trade ID-ის მიხედვით."""
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


# ---------------------------------------------------------------- settings
@st.cache_data(ttl=SETTINGS_TTL, show_spinner=False)
def _load_settings(uid, category):
  response = (
      get_data_client()
      .table("user_settings")
      .select("item_name")
      .eq("category", category)
      .execute()
  )
  return [row["item_name"] for row in response.data] if response.data else []


def fetch_settings(category):
  """კატეგორიის მიხედვით სიის წამოღება ბაზიდან."""
  try:
    return _load_settings(_uid(), category)
  except Exception:
    if category == "pattern":
      return ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"]
    return ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]


def add_setting_item(category, item_name):
  try:
    get_data_client().table("user_settings").insert(
        {"category": category, "item_name": item_name}
    ).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


def delete_setting_item(category, item_name):
  try:
    get_data_client().table("user_settings").delete().eq(
        "category", category
    ).eq("item_name", item_name).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


def update_setting_item(category, old_name, new_name):
  try:
    get_data_client().table("user_settings").update(
        {"item_name": new_name}
    ).eq("category", category).eq("item_name", old_name).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


# ------------------------------------------------------- balance transactions
@st.cache_data(ttl=BALANCE_TTL, show_spinner=False)
def _load_balance(uid):
  response = get_data_client().table("balance_transactions").select("*").execute()
  return (
      pd.DataFrame(response.data)
      if response.data
      else pd.DataFrame(columns=BALANCE_COLUMNS)
  )


def fetch_balance_transactions():
  """ბრუნავს ტრანზაქციების DataFrame-ს."""
  try:
    return _load_balance(_uid())
  except Exception:
    return pd.DataFrame(columns=BALANCE_COLUMNS)


def add_balance_transaction(data):
  """ახალი ტრანზაქციის დამატება ბაზაში."""
  try:
    get_data_client().table("balance_transactions").insert(data).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    st.error(f"შეცდომა ბაზაში ჩაწერისას: {e}")
    return False


def delete_balance_transaction(txn_id):
  """ტრანზაქციის წაშლა ID-ის მიხედვით."""
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
  """მოაქვს მომხმარებლის ვიზუალური პარამეტრები ბაზიდან."""
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
  """ანახლებს ან ამატებს მომხმარებლის პარამეტრებს ბაზაში."""
  try:
    data = {"user_id": user_id}
    if mobile_mode is not None:
      data["mobile_view_mode"] = mobile_mode
    if desktop_mode is not None:
      data["desktop_view_mode"] = desktop_mode

    get_data_client().table("user_preferences").upsert(
        data, on_conflict="user_id"
    ).execute()
    return True
  except Exception as e:
    st.error(f"ბაზის დეტალური შეცდომა: {e}")
    return False


def fetch_all_user_preferences():
  """ადმინისთვის: იღებს ყველა მომხმარებლის პარამეტრებსა და ბალანსს"""
  supabase = get_data_client()
  try:
    res = supabase.table("user_preferences").select("*").execute()
    return pd.DataFrame(res.data) if res.data else pd.DataFrame()
  except Exception as e:
    st.error(f"მომხმარებლების წამოღების შეცდომა: {e}")
    return pd.DataFrame()


def admin_update_user_credits(user_id: str, new_balance: float):
  """ადმინისთვის: პირდაპირ ცვლის მომხმარებლის კრედიტების ბალანსს"""
  supabase = get_data_client()
  try:
    supabase.table("user_preferences").update(
        {"credits_balance": float(new_balance)}
    ).eq("user_id", user_id).execute()
    return True
  except Exception as e:
    st.error(f"კრედიტების განახლების შეცდომა: {e}")
    return False
