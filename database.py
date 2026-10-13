from database import fetch_trades, insert_trade  # ან უბრალოდ შენი ძველი კოდი
import pandas as pd
import streamlit as st
from supabase import create_client


def get_supabase_client():
  # კოდი ეძებს სექრეტებში ჩაწერილ გასაღებებს
  supabase_url = st.secrets["SUPABASE_URL"]
  supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN1bGlmbWdjZGJsdnVmbXlnanBnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE4MTMxOTAsImV4cCI6MjEwNzM4OTE5MH0.nKibVuu0NM4qjnVNX9i71GLfp2fqnoxlC7EAJhXQx8I"
#  supabase_key = st.secrets["SUPABASE_KEY"]
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
