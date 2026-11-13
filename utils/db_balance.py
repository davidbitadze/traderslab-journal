import pandas as pd
import streamlit as st
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
