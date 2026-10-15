from database import fetch_trades
import pandas as pd
import streamlit as st


def render_analytics_view(lang="ka"):
  st.title("📈 სტატისტიკა და ანალიტიკა (Analytics)")
  st.divider()

  df = fetch_trades()

  if df.empty:
    st.info("ანალიტიკისთვის მონაცემები ჯერ არ არის ჟურნალში.")
    return

  # 1. მთავარი გარიგებების იდენტიფიკაცია (Start Row)
  main_trades = df[
      df["ActionType"].str.contains("Start Row", case=False, na=False)
  ]
  if main_trades.empty:
    main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

  analyzed_trades = []

  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    side = trade.get("Side", "Long")

    pattern = trade.get("Pattern") or trade.get("Formation") or "N/A"
    if pd.isna(pattern) or not pattern:
      pattern = "N/A"

    trigger = trade.get("Trigger") or "N/A"
    if pd.isna(trigger) or not trigger:
      trigger = "N/A"

    # ვამოწმებთ Finalized სტატუსს
    is_fin = trade.get("Finalized", False)
    if isinstance(is_fin, str):
      is_fin = is_fin.lower() == "true"

    # თუ გარიგება არ არის დასრულებული (Finalized არ არის True), გამოვტოვებთ ანალიტიკიდან
    if not is_fin:
      continue

    # ვკრიბავთ Net P/L-ს ბაზიდან
    sub_actions = df[
        (df["Parent Trade ID"] == trade_id) | (df["Trade ID"] == trade_id)
    ]
    total_pnl = 0.0
    for _, sub in sub_actions.iterrows():
      pnl_val = sub.get("Net P/L", 0)
      try:
        if pnl_val and not pd.isna(pnl_val):
          total_pnl += float(pnl_val)
      except:
        pass

    analyzed_trades.append({
        "Trade ID": trade_id,
        "Pair": trade.get("Pair", "N/A"),
        "Side": side,
        "Pattern": str(pattern),
        "Trigger": str(trigger),
        "PnL": total_pnl,
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
      st.metric("მოგებიანობა (Win Rate)", f"{win_rate:.1f}%")
    with col3:
      st.metric("მოგებათა რაოდენობა", len(winning_trades))
    with col4:
      st.metric("წაგებათა რაოდენობა", len(losing_trades))

    st.divider()

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
    st.info(
        "დასრულებული (Finalized) გარიგებები ანალიტიკისთვის ჯერ არ მოიძებნა."
    )
