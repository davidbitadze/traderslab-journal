import streamlit as st
from utils.db_core import get_data_client, _uid

SETTINGS_TTL = 600

@st.cache_data(ttl=SETTINGS_TTL, show_spinner=False)
def _load_settings(uid, category):
  if not uid:
    return []
  client = get_data_client()
  response = (
      client.table("user_settings")
      .select("item_name")
      .eq("category", category)
      .eq("user_id", uid)
      .execute()
  )
  items = [row["item_name"] for row in response.data] if response.data else []

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
            "item_name": d,
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
    return []

def add_setting_item(category, item_name):
  try:
    uid = _uid()
    if not uid or not item_name.strip():
      return False
    get_data_client().table("user_settings").insert(
        {"category": category, "item_name": item_name.strip(), "user_id": uid}
    ).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False

def delete_setting_item(category, item_name):
  try:
    uid = _uid()
    if not uid:
      return False
    get_data_client().table("user_settings").delete().eq(
        "category", category
    ).eq("item_name", item_name).eq("user_id", uid).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False

def update_setting_item(category, old_name, new_name):
  try:
    uid = _uid()
    if not uid or not new_name.strip():
      return False
    get_data_client().table("user_settings").update(
        {"item_name": new_name.strip()}
    ).eq("category", category).eq("item_name", old_name).eq("user_id", uid).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False
