from database import fetch_balance_transactions, fetch_trades
import pandas as pd
import streamlit as st
from utils.formulas import calculate_net_pnl, to_float
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import recalc_all_net_pnl, render_trade_card


def render_journal_view(lang="ka"):
  # 1. ვიღებთ დეპოზიტების/ტრანზაქციების ჯამს
  df_txn = fetch_balance_transactions()
  total_deposits = 500.0  # ნაგულისხმევად თუ ტრანზაქცია არ არის
  if not df_txn.empty and "Amount" in df_txn.columns:
    total_deposits = pd.to_numeric(df_txn["Amount"], errors="coerce").sum()

  # 2. მონაცემების წამოღება გარიგებებიდან
  df = fetch_trades()
  
  if not df.empty and "Entry Date" in df.columns:
      # mixed ფორმატი უზრუნველყოფს, რომ როგორც 'YYYY-MM-DD', ისე 'MM/DD/YYYY' სწორად დაკონვერტირდეს
      df["parsed_date"] = pd.to_datetime(df["Entry Date"], errors="coerce", format="mixed")
      df = df.sort_values(by="parsed_date", ascending=False).drop(columns=["parsed_date"])
    

  # 2.1 Net P/L-ის სინქრონიზაცია ბაზასთან: ერთხელ სესიაზე (გვერდის ჩატვირთვა/რეფრეში)
  if not df.empty and not st.session_state.get("net_pnl_synced"):
    st.session_state["net_pnl_synced"] = True
    try:
      recalc_all_net_pnl(df)
    except Exception:
      pass  # სინქრონიზაციის შეცდომამ გვერდი არ უნდა გააჩეროს

  # 3. ჯამური PnL: იგივე ფორმულა, რაც ბარათებზეა (utils/formulas.py)
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


  # 5. კომპაქტური, მობილურზე მორგებული სათაური (Glide-ის სტილში)
  st.markdown(
      f"""
      <h3 style='margin-bottom: 0px; font-size: 22px; font-weight: 600;'>
          📊 სავაჭრო ჟურნალი — <span style='color: #4CAF50;'>{final_balance:.2f}$</span>
      </h3>
      """,
      unsafe_allow_html=True
  )

# 6. ახალი გარიგების დამატების მოდალი
  render_add_trade_modal()
  
  st.divider()
  
  if not df.empty:
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])
  
# 🔄 სორტირება: თარიღის მიხედვით ახლიდან ძველისკენ (Descending)
    if "Entry Date" in main_trades.columns:
      main_trades = main_trades.copy()
      main_trades["parsed_date"] = pd.to_datetime(
          main_trades["Entry Date"], errors="coerce", format="mixed"
      )
      main_trades = main_trades.sort_values(
          by="parsed_date", ascending=False
      ).drop(columns=["parsed_date"])
      
    # თითოეული გარიგებისთვის გამოვიძახებთ ცალკეულ კომპონენტს
    for index, trade in main_trades.iterrows():
      render_trade_card(trade, df)
  
  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
