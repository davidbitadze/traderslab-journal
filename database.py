import pandas as pd
from supabase import create_client
import streamlit as st

# Supabase კავშირის პარამეტრები
SUPABASE_URL = "https://sulifmgcdblvufmygjpg.supabase.co"
SUPABASE_KEY = "sb_publishable_74vvbyKYiZ-8fFXdGfd0zQ_Ezk57..."


def get_supabase_client():
  return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_trades():
  try:
    supabase = get_supabase_client()
    response = supabase.table("trades").select("*").execute()
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()
  except Exception as e:
    st.error(f"ბაზიდან მონაცემის წამოღების შეცდომა: {e}")
    return pd.DataFrame()


def insert_trade(trade_data):
  try:
    supabase = get_supabase_client()
    response = supabase.table("trades").insert(trade_data).execute()
    return True
  except Exception as e:
    st.error(f"ბაზაში ჩაწერის შეცდომა: {e}")
    return False
