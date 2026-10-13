from database import fetch_trades
import streamlit as st
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import render_trade_card  # ახალი ცალკეული კომპონენტი


def render_journal_view(lang="ka"):
  st.title("📊 სავაჭრო ჟურნალი (Trading Journal)")

  # 1. ახალი გარიგების დამატების მოდალი
  render_add_trade_modal()

  st.divider()

  # 2. მონაცემების წამოღება
  df = fetch_trades()

  if not df.empty:
    st.subheader("📋 აქტიური და ისტორიული პოზიციები")

    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    # თითოეული გარიგებისთვის გამოვიძახებთ ცალკეულ კომპონენტს
    for index, trade in main_trades.iterrows():
      render_trade_card(trade, df)

  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
