import pandas as pd
import streamlit as st
from database import fetch_balance_transactions, fetch_trades
from utils.credits import get_user_credits
from utils.formulas import calculate_net_pnl, to_float
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import render_trade_card


def render_journal_view(lang="ka"):
  # 1. ვიღებთ დეპოზიტების/ტრანზაქციების ჯამს
  df_txn = fetch_balance_transactions()
  total_deposits = 500.0
  if not df_txn.empty and "Amount" in df_txn.columns:
    total_deposits = pd.to_numeric(df_txn["Amount"], errors="coerce").sum()

  # 2. მონაცემების წამოღება გარიგებებიდან
  df = fetch_trades()

  if not df.empty and "Entry Date" in df.columns:
    df["parsed_date"] = pd.to_datetime(
        df["Entry Date"], errors="coerce", format="mixed"
    )
    df = df.sort_values(by="parsed_date", ascending=False).drop(
        columns=["parsed_date"]
    )

  # 3. ჯამური PnL-ის კალკულაცია
  total_pnl = 0.0
  if not df.empty:
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    for _, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      sub_actions = df[df["Parent Trade ID"] == trade_id]
      pnl = calculate_net_pnl(trade, sub_actions)
      if pnl is None:
        pnl = to_float(trade.get("Net P/L"))
      total_pnl += pnl

  # 4. საბოლოო ბალანსი = დეპოზიტების ჯამი + ჯამური PnL
  final_balance = total_deposits + total_pnl

  # 5. AI ქულების ბალანსის წამოღება
  user_id = st.session_state.user.id if st.session_state.user else None
  ai_credits = get_user_credits(user_id) if user_id else 0.0

  # 6. სათაური ფინანსური და AI ბალანსით
  st.markdown(
      f"""
      <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
          <h3 style='margin: 0px; font-size: 20px; font-weight: 600;'>
              📊 სავაჭრო ჟურნალი — <span style='color: #4CAF50;'>{final_balance:.2f}$</span>
          </h3>
          <span style='background-color: #1E293B; border: 1px solid #334155; padding: 4px 10px; border-radius: 8px; font-size: 13px; font-weight: 500; color: #38BDF8;'>
              💳 ბალანსი: <b>{ai_credits:g} ქულა</b>
          </span>
      </div>
      """,
      unsafe_allow_html=True,
  )

  # 7. ახალი გარიგების დამატების მოდალი
  render_add_trade_modal()

  st.divider()

  if not df.empty:
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    for _, trade in main_trades.iterrows():
      render_trade_card(trade, df)

  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
