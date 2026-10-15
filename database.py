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
    response = (
        supabase.table("trades")
        .select("*")
        .order("Entry Date", desc=True)
        .execute()
    )
    return pd.DataFrame(response.data) if response.data else pd.DataFrame()
  except Exception as e:
    st.error(f"ბაზიდან მონაცემის წამოღების შეცდომა: {e}")
    return pd.DataFrame()


def insert_trade(trade_data):
  try:
    supabase = get_supabase_client()
    supabase.table("trades").insert(trade_data).execute()
    return True
  except Exception as e:
    st.error(f"ბაზაში ჩაწერის შეცდომა: {e}")
    return False


# database.py-ის დამატებითი ფუნქციები პარამეტრებისთვის


def fetch_settings(category):
  """კატეგორიის მიხედვით (მაგ: 'pattern' ან 'trigger') სიის წამოღება ბაზიდან"""
  try:
    supabase = get_supabase_client()
    response = (
        supabase.table("user_settings")
        .select("*")
        .eq("category", category)
        .execute()
    )
    return [row["item_name"] for row in response.data] if response.data else []
  except Exception:
    # საწყისი დეფოლტები თუ ცხრილი ჯერ ცარიელია
    if category == "pattern":
      return ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"]
    else:
      return ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]


def add_setting_item(category, item_name):
  try:
    supabase = get_supabase_client()
    supabase.table("user_settings").insert(
        {"category": category, "item_name": item_name}
    ).execute()
    return True
  except Exception as e:
    return False


def delete_setting_item(category, item_name):
  try:
    supabase = get_supabase_client()
    supabase.table("user_settings").delete().eq("category", category).eq(
        "item_name", item_name
    ).execute()
    return True
  except Exception as e:
    return False


def update_setting_item(category, old_name, new_name):
  try:
    supabase = get_supabase_client()
    supabase.table("user_settings").update({"item_name": new_name}).eq(
        "category", category
    ).eq("item_name", old_name).execute()
    return True
  except Exception as e:
    return False


def update_trade(trade_id, updated_data):
  """არსებული გარიგების მონაცემების განახლება Supabase-ში Trade ID-ის მიხედვით"""
  try:
    supabase = get_supabase_client()
    # ვცდილობთ განახლებას Trade ID სვეტით
    response = (
        supabase.table("trades")
        .update(updated_data)
        .eq("Trade ID", trade_id)
        .execute()
    )
    return True
  except Exception as e:
    st.error(f"ბაზის განახლების შეცდომა: {e}")
    return False


def delete_trade(trade_id):
  """გარიგების და მასთან დაკავშირებული ქვემოქმედებების წაშლა Trade ID-ის მიხედვით"""
  try:
    supabase = get_supabase_client()
    supabase.table("trades").delete().eq("Trade ID", trade_id).execute()
    supabase.table("trades").delete().eq("Parent Trade ID", trade_id).execute()
    return True
  except Exception as e:
    st.error(f"ბაზიდან წაშლის შეცდომა: {e}")
    return False


# საწყისი დეპოზიტის/ტრანზაქციების წამოღება ბაზიდან


def fetch_balance_transactions():
  """ბრუნავს ტრანზაქციების DataFrame-ს ან სიას."""
  try:
    supabase = get_supabase_client()
    response = supabase.table("balance_transactions").select("*").execute()
    return (
        pd.DataFrame(response.data)
        if response.data
        else pd.DataFrame(
            columns=["Transaction ID", "Date", "Amount", "Description"]
        )
    )
  except Exception as e:
    return pd.DataFrame(
        columns=["Transaction ID", "Date", "Amount", "Description"]
    )


def add_balance_transaction(data):
  """ახალი ტრანზაქციის (შევსება/გამოტანა) დამატება ბაზაში."""
  try:
    supabase = get_supabase_client()
    supabase.table("balance_transactions").insert(data).execute()
    return True
  except Exception as e:
    st.error(f"შეცდომა ბაზაში ჩაწერისას: {e}")
    return False


def delete_balance_transaction(txn_id):
  """ტრანზაქციის წაშლა ID-ის მიხედვით."""
  try:
    supabase = get_supabase_client()
    supabase.table("balance_transactions").delete().eq(
        "Transaction ID", txn_id
    ).execute()
    return True
  except Exception as e:
    st.error(f"შეცდომა ტრანზაქციის წაშლისას: {e}")
    return False
