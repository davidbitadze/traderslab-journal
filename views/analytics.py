from database import fetch_trades
import pandas as pd
import streamlit as st
from utils.formulas import calculate_trade_pnl


def render_analytics_view(lang="ka"):
  st.title("📈 სტატისტიკა და ანალიტიკა (Analytics)")
  st.divider()

  df = fetch_trades()

  if df.empty:
    st.info("ანალიტიკისთვის მონაცემები ჯერ არ არის ჟურნალში.")
    return

  # 1. მთავარი გარიგებების იდენტიფიკაცია (სადაც Parent Trade ID ცარიელია ან None)
  if "Parent Trade ID" in df.columns:
    main_trades = df[
        df["Parent Trade ID"].isna()
        | (df["Parent Trade ID"] == "")
        | (df["Parent Trade ID"].astype(str).str.lower() == "none")
    ]
  else:
    main_trades = df.drop_duplicates(subset=["Trade ID"])

  if main_trades.empty:
    main_trades = df.head(2)  # ფოლბექი უსაფრთხოებისთვის

  analyzed_trades = []

  # 2. თითოეული მთავარი გარიგებისთვის PnL-ის და დეტალების გამოთვლა
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID")
    entry_price = float(trade.get("Entry Price", 0) or 0)
    risk_val = float(trade.get("Risk ($)", 5.85) or 5.85)
    side = trade.get("Side", "Long")

    pattern = trade.get("Pattern", "N/A")
    if not pattern or pd.isna(pattern):
      pattern = "N/A"

    trigger = trade.get("Trigger", "N/A")
    if not trigger or pd.isna(trigger):
      trigger = "N/A"

    is_fin = str(trade.get("Finalized", "False")).lower() == "true"

    # ვეძებთ ამ გარიგების ყველა სუბ-მოქმედებას (Exits) სადაც Parent Trade ID == trade_id
    sub_actions = df[df["Parent Trade ID"] == trade_id]
    exits = sub_actions[
        sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
    ]

    trade_pnl = 0.0
    if not exits.empty:
      for _, ex in exits.iterrows():
        ex_price = float(ex.get("Entry Price", entry_price) or entry_price)
        pnl_part = calculate_trade_pnl(entry_price, ex_price, risk_val, side)
        trade_pnl += pnl_part
    else:
      if is_fin:
        trade_pnl = calculate_trade_pnl(
            entry_price, entry_price, risk_val, side
        )
      else:
        trade_pnl = 0.0

    analyzed_trades.append({
        "Trade ID": trade_id,
        "Pair": trade.get("Pair", "N/A"),
        "Side": side,
        "Pattern": pattern,
        "Trigger": trigger,
        "PnL": trade_pnl,
    })

  df_analytics = pd.DataFrame(analyzed_trades)

  if not df_analytics.empty:
    # მთავარი KPI მეტრიკები
    total_pnl = df_analytics["PnL"].sum()
    winning_trades = df_analytics[df_analytics["PnL"] > 0]
    losing_trades = df_analytics[df_analytics["PnL"] < 0]

    win_rate = (
        (len(winning_trades) / len(df_analytics)) * 100
        if len(df_analytics) > 0
        else 0
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
      st.metric("ჯამური PnL", f"{total_pnl:+.2f}$")
    with col2:
      st.metric("მოგებიანობა (Win Rate)", f"{win_rate:.1f}%")
    with col3:
      st.metric("მოგებათა რაოდენობა", len(winning_trades))
    with col4:
      st.metric("წაგებათა რაოდენობა", len(losing_trades))

    st.divider()

    # პატერნების მიხედვით დაჯგუფება
    st.subheader("📌 პატერნების ანალიზი (Patterns)")
    pattern_grouped = (
        df_analytics.groupby("Pattern")
        .agg(
            ტრანზაქცია=("PnL", "count"),
            ჯამური_PnL=("PnL", "sum"),
            საშუალო_PnL=("PnL", "mean"),
        )
        .reset_index()
    )
    st.dataframe(pattern_grouped, use_container_width=True)

    # ტრიგერების მიხედვით დაჯგუფება
    st.subheader("⚡ ტრიგერების ანალიზი (Triggers)")
    trigger_grouped = (
        df_analytics.groupby("Trigger")
        .agg(
            ტრანზაქცია=("PnL", "count"),
            ჯამური_PnL=("PnL", "sum"),
            საშუალო_PnL=("PnL", "mean"),
        )
        .reset_index()
    )
    st.dataframe(trigger_grouped, use_container_width=True)

  else:
    st.info("ანალიტიკური მონაცემები ჯერ ვერ დამუშავდა.")
