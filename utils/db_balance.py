import pandas as pd
import streamlit as st
from i18n import t
from utils.db_core import get_data_client, _uid

BALANCE_TTL = 300
BALANCE_COLUMNS = ["Transaction ID", "Date", "Amount", "Description"]

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
    print(f"db_balance.py: {e!r}")  # დეტალი მხოლოდ ლოგში
    st.error(t("db_generic_error", st.session_state.get("lang", "ka")))
    return False

def delete_balance_transaction(txn_id):
  try:
    get_data_client().table("balance_transactions").delete().eq(
        "Transaction ID", txn_id
    ).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    print(f"db_balance.py: {e!r}")  # დეტალი მხოლოდ ლოგში
    st.error(t("db_generic_error", st.session_state.get("lang", "ka")))
    return False
