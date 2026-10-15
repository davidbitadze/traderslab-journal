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

  # მთავარი გარიგებების ზუსტი ფილტრაცია (იგივე ლოგიკა, რაც ჟურნალშია)
  main_trades = df[
      df["ActionType"].str.contains("Start Row", case=False, na=False)
  ]
  if main_trades.empty:
    main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

  total_trades_count = len(main_trades)
  st.subheader(f"სულ მთავარი გარიგებები: {total_trades_count}")

  analyzed_trades = []

  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    entry_price = float(trade.get("Entry Price", 0) or 0)
    risk_val = float(trade.get("Risk ($)", 5.85) or 5.85)
    side = trade.get("Side", "Long")
    pattern = (
        trade.get("Formation")
        or trade.get("Pattern")
        or trade.get("Description", "N/A")
    )
    is_fin = str(trade.get("Finalized", "False")).lower() == "true"

    # ვეძებთ ამ გარიგების ყველა სუბ-მოქმედებას (Exits)
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
        "PnL": trade_pnl,
    })

  df_analytics = pd.DataFrame(analyzed_trades)

  if not df_analytics.empty:
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
      st.metric("მოგებიანი გარიგებები", f"{win_rate:.1f}%")
    with col3:
      st.metric("მოგებათა რაოდენობა", len(winning_trades))
    with col4:
      st.metric("წაგებათა რაოდენობა", len(losing_trades))

    st.divider()

    st.subheader("📋 დამუშავებული გარიგებების სია")
    st.dataframe(df_analytics, use_container_width=True)

    st.divider()

    st.subheader("📌 პატერნების ანალიზი")
    pattern_grouped = (
        df_analytics.groupby("Pattern")
        .agg(
            Count=("PnL", "count"),
            Total_PnL=("PnL", "sum"),
            Avg_PnL=("PnL", "mean"),
        )
        .reset_index()
    )

    st.dataframe(pattern_grouped, use_container_width=True)

  else:
    st.info("ანალიტიკური მონაცემები ჯერ ვერ დამუშავდა.")
