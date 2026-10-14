from database import fetch_balance_transactions, fetch_trades
import streamlit as st
from utils.formulas import calculate_trade_pnl
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import render_trade_card


def render_journal_view(lang="ka"):
  # 1. ვიღებთ დეპოზიტების/ტრანზაქციების ჯამს
  df_txn = fetch_balance_transactions()
  total_deposits = 500.0  # ნაგულისხმევად თუ ტრანზაქცია არ არის
  if not df_txn.empty and "Amount" in df_txn.columns:
    total_deposits = pd.to_numeric(df_txn["Amount"], errors="coerce").sum()

  # 2. მონაცემების წამოღება გარიგებებიდან
  df = fetch_trades()

  # 3. ვთვლით ჯამურ PnL-ს ყველა გარიგებიდან
  total_pnl = 0.0
  if not df.empty:
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    for _, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      entry_price = float(trade.get("Entry Price", 0) or 0)
      risk_val = float(trade.get("Risk ($)", 0) or 0)
      side = trade.get("Side", "Long")
      is_fin = (
          str(trade.get("Finalized", "False")).lower() == "true"
      )

      sub_actions = df[df["Parent Trade ID"] == trade_id]
      exits = sub_actions[
          sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
      ]

      exit_price = entry_price
      if not exits.empty:
        exit_price = float(
            exits.iloc[-1].get("Entry Price", entry_price) or entry_price
        )
      else:
        if is_fin:
          exit_price = entry_price

      pnl = calculate_trade_pnl(entry_price, exit_price, risk_val, side)
      total_pnl += pnl

  # 4. საბოლოო ბალანსი = დეპოზიტების ჯამი + ჯამური PnL
  final_balance = total_deposits + total_pnl

  # 5. დინამიკური სათაური ბალანსით
  st.title(f"📊 სავაჭრო ჟურნალი — {final_balance:.2f}$")

  # 6. ახალი გარიგების დამატების მოდალი
  render_add_trade_modal()

  st.divider()

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
