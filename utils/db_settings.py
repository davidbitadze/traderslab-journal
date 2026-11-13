import streamlit as st
from utils.db_core import get_data_client, _uid

SETTINGS_TTL = 600

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

  # თუ იუზერს ამ კატეგორიაში ჩანაწერი არ აქვს, ვუწერთ საწყის 3-3 დეფოლტს
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
  except Exception as e:
    st.error(f"წაშლის შეცდომა: {e}")
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
  except Exception as e:
    st.error(f"განახლების შეცდომა: {e}")
    return False
