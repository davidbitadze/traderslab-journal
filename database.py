import pandas as pd
import streamlit as st

# იმპორტები ახალი გამოყოფილი მოდულებიდან
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
  """[(trade_id, net_pnl)] -> ბაზაში მხოლოდ Net P/L-ის განახლება; ქეში ბოლოს ერთხელ იწმინდება.
  აბრუნებს წარმატებით ჩაწერილ წყვილებს. შეცდომა არასდროს ჩერდება მომხმარებლის ეკრანზე."""
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
  if not uid:
    return []
  response = (
      get_data_client()
      .table("user_settings")
      .select("item_name")
      .eq("category", category)
      .eq("user_id", uid)  # RLS-ის გარდა, კოდშიც ვფილტრავთ (ორმაგი დაცვა)
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
  """ანახლებს მომხმარებლის ეკრანის ზომის პარამეტრებს (მხოლოდ უსაფრთხო სვეტებს).
  რიგი ბაზაში უკვე არსებობს (იქმნება ავტომატურად), ამიტომ UPDATE საკმარისია."""
  data = {}
  if mobile_mode is not None:
    data["mobile_view_mode"] = mobile_mode
  if desktop_mode is not None:
    data["desktop_view_mode"] = desktop_mode
  return update_user_preference_fields(user_id, **data)


# სვეტები, რომელთა შეცვლაც თავად მომხმარებელს შეუძლია (იხ. sql/001_security_and_admin.sql)
EDITABLE_PREFERENCE_FIELDS = ("language", "theme", "mobile_view_mode", "desktop_view_mode")


def update_user_preference_fields(user_id, **fields):
  """ცვლის მხოლოდ დაშვებულ პარამეტრებს (ენა, თემა, ზომები). კრედიტები და გამოწერა
  აქედან არ იცვლება: ბაზაც კრძალავს და აქაც არ ვუშვებთ."""
  data = {k: v for k, v in fields.items() if k in EDITABLE_PREFERENCE_FIELDS}
  if not data:
    return True
  try:
    get_data_client().table("user_preferences").update(data).eq("user_id", user_id).execute()
    # სესიაში შენახული ასლიც ვანახლოთ, რომ შემდეგი rerun-ი ძველ მნიშვნელობას არ დაუბრუნდეს
    cached = st.session_state.get("user_prefs")
    if isinstance(cached, dict):
      cached.update(data)
    return True
  except Exception as e:
    st.error(f"ბაზის დეტალური შეცდომა: {e}")
    return False


# ----------------------------------------------------------------- RPC helpers
def ensure_user_preferences():
  """თუ ამ მომხმარებელს პარამეტრების რიგი არ აქვს (ძველი ანგარიში), ბაზა ქმნის ნაგულისხმევს."""
  data, error = call_rpc("ensure_my_preferences")
  if error or not isinstance(data, dict):
    return None
  return data


def fetch_my_staff_role():
  """'admin' | 'mentor' | None. თუ ფუნქცია ბაზაში არ არის ან შეცდომაა, წვდომა არ გაიცემა."""
  data, error = call_rpc("my_staff_role")
  if error:
    return None
  if isinstance(data, list):
    data = data[0] if data else None
  return data if data in ("admin", "mentor") else None
