import streamlit as st
from utils.db_core import get_data_client, call_rpc

EDITABLE_PREFERENCE_FIELDS = ("language", "theme", "mobile_view_mode", "desktop_view_mode")

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
