import pandas as pd
import streamlit as st
from supabase import create_client


def get_supabase_client():
  # ვიყენებთ სექრეტებში ჩაწერილ გასაღებებს
  supabase_url = st.secrets["SUPABASE_URL"]
  supabase_key = st.secrets["SUPABASE_KEY"]
  return create_client(supabase_url, supabase_key)


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
