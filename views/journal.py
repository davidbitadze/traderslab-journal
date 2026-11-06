import pandas as pd
import streamlit as st
from database import fetch_balance_transactions, fetch_trades
from utils.credits import get_user_credits_cached
from utils.formulas import calculate_net_pnl, to_float
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import inject_card_css, render_trade_card

PAGE_SIZE = 30  # ერთდროულად ნაჩვენები ბარათების რაოდენობა


def render_journal_view(lang="ka"):
  # 1. ვიღებთ დეპოზიტების/ტრანზაქციების ჯამს
  df_txn = fetch_balance_transactions()
  total_deposits = 500.0
  if not df_txn.empty and "Amount" in df_txn.columns:
    total_deposits = pd.to_numeric(df_txn["Amount"], errors="coerce").sum()

  # 2. მონაცემების წამოღება გარიგებებიდან (ქეშიდან: ბაზას მხოლოდ ცვლილების შემდეგ ეკითხება)
  df = fetch_trades()

  main_trades = pd.DataFrame()
  subs_map = {}
  pnl_map = {}
  total_pnl = 0.0

  if not df.empty:
    # ერთჯერადი სორტირება თარიღით
    if "Entry Date" in df.columns:
      df["_parsed_date"] = pd.to_datetime(
          df["Entry Date"], errors="coerce", format="mixed"
      )
      df = df.sort_values(by="_parsed_date", ascending=False).drop(
          columns=["_parsed_date"]
      )

    # 3. მთავარი გარიგებები (ერთხელ ითვლება, ორჯერ აღარ)
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    # ქვეეტაპები ერთი groupby-თი (ნაცვლად ყოველი ბარათისთვის მთელი ცხრილის გაფილტვრისა)
    subs_map = {pid: g for pid, g in df.groupby("Parent Trade ID", sort=False)}
    empty_subs = df.iloc[0:0]

    # ჯამური PnL; იგივე შედეგი ბარათებსაც გადაეცემა და ხელახლა აღარ ითვლება
    for _, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      pnl = calculate_net_pnl(trade, subs_map.get(trade_id, empty_subs))
      if pnl is None:
        pnl = to_float(trade.get("Net P/L"))
      pnl_map[trade_id] = pnl
      total_pnl += pnl

  # 4. საბოლოო ბალანსი = დეპოზიტების ჯამი + ჯამური PnL
  final_balance = total_deposits + total_pnl

  # 5. AI ქულების ბალანსი (ჩვენებისთვის: სესიის ქეშიდან, ყოველ rerun-ზე ბაზაში აღარ მიდის)
  user_id = st.session_state.user.id if st.session_state.user else None
  ai_credits = get_user_credits_cached(user_id) if user_id else 0.0

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

  if df.empty:
    st.info("ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
    return

  # 8. ბარათები: CSS ერთხელ, ბარათები გვერდ-გვერდ (პაგინაცია)
  inject_card_css()

  limit = st.session_state.get("journal_limit", PAGE_SIZE)
  total_count = len(main_trades)

  for _, trade in main_trades.head(limit).iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    render_trade_card(
        trade,
        df,
        subs=subs_map.get(trade_id),
        pnl=pnl_map.get(trade_id),
    )

  if total_count > limit:
    if st.button(
        f"⬇️ მეტის ჩვენება ({limit} / {total_count})",
        use_container_width=True,
        key="journal_show_more",
    ):
      st.session_state["journal_limit"] = limit + PAGE_SIZE
      st.rerun()
