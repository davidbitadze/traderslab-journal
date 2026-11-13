import pandas as pd
import streamlit as st
from database import fetch_balance_transactions, fetch_trades, update_net_pnl_batch
from utils.credits import get_user_credits_cached
from utils.trades import compute_pnl_map, split_trades, stale_net_pnl
from utils.translations import t
from views.add_trade_modal import render_add_trade_modal
from views.trade_card import inject_card_css, render_trade_card

PAGE_SIZE = 30  # ერთდროულად ნაჩვენები ბარათების რაოდენობა
SYNC_TRIED_KEY = "_pnl_sync_tried"


def _sync_stored_net_pnl(main_trades, subs_map):
  """ბაზის Net P/L სვეტს ასწორებს ცოცხალ გამოთვლასთან. ერთი და იგივე მნიშვნელობა სესიაში
  მეორედ არ იწერება, ამიტომ ჩაწერის (მაგ. უფლების) შეცდომა ციკლში ვერ ჩავარდება."""
  tried = st.session_state.setdefault(SYNC_TRIED_KEY, set())
  try:
    stale = stale_net_pnl(main_trades, subs_map, tried)
    if not stale:
      return
    tried.update((trade_id, str(value)) for trade_id, value in stale)
    update_net_pnl_batch(stale)
  except Exception:
    pass


def render_journal_view(lang="ka"):
  # 1. ვიღებთ დეპოზიტების/ტრანზაქციების ჯამს
  df_txn = fetch_balance_transactions()
  total_deposits = 500.0
  if not df_txn.empty and "Amount" in df_txn.columns:
    total_deposits = pd.to_numeric(df_txn["Amount"], errors="coerce").sum()

  # 2. მონაცემების წამოღება გარიგებებიდან (ქეშიდან: ბაზას მხოლოდ ცვლილების შემდეგ ეკითხება)
  df = fetch_trades()

  main_trades, subs_map = split_trades(df)
  pnl_map = compute_pnl_map(main_trades, subs_map)
  total_pnl = float(sum(pnl_map.values()))

  # ბაზაში შენახული Net P/L (Sheets-ისთვის, ექსპორტისთვის) სესიაში ერთხელ ახლდება მხოლოდ
  # იმ გარიგებებზე, სადაც განსხვავდება; ზედმეტი ჩაწერა არ ხდება.
  _sync_stored_net_pnl(main_trades, subs_map)

  # 4. საბოლოო ბალანსი = დეპოზიტების ჯამი + ჯამური PnL
  final_balance = total_deposits + total_pnl

  # 5. AI ქულების ბალანსი (ჩვენებისთვის: სესიის ქეშიდან, ყოველ rerun-ზე ბაზაში აღარ მიდის)
  user_id = st.session_state.user.id if st.session_state.user else None
  ai_credits = get_user_credits_cached(user_id) if user_id else 0.0

  # დინამიური ლეიბლები ენის მიხედვით
  journal_title_str = t("journal_title", lang) if "journal_title" in t(lang) else ("Trade Journal" if lang == "en" else "სავაჭრო ჟურნალი")
  balance_label_str = t("credits", lang) if "credits" in t(lang) else ("Balance" if lang == "en" else "ბალანსი")
  credit_unit_str = t("credit_unit", lang) if "credit_unit" in t(lang) else ("credits" if lang == "en" else "ქულა")

# თემის მიხედვით ბალანსის ვიჯეტის ფერები
  is_light = st.session_state.get("theme", "dark") == "light"
  bal_bg = "#FFFFFF" if is_light else "#1E293B"
  bal_border = "#CBD5E1" if is_light else "#334155"
  bal_text = "#0F172A" if is_light else "#38BDF8"
  bal_card_bg = "#F8FAFC" if is_light else "#121926"

  # 6. სათაური ფინანსური და AI ბალანსით
  st.markdown(
      f"""
      <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;'>
          <h3 style='margin: 0px; font-size: 20px; font-weight: 600;'>
              📊 {journal_title_str} — <span style='color: #4CAF50;'>{final_balance:.2f}$</span>
          </h3>
          <span style='background-color: {bal_bg}; border: 1px solid {bal_border}; padding: 4px 10px; border-radius: 8px; font-size: 13px; font-weight: 500; color: {bal_text}; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
              💳 {balance_label_str}: <b style='color: {bal_text};'>{ai_credits:g} {credit_unit_str}</b>
          </span>
      </div>
      """,
      unsafe_allow_html=True,
  )

  # 7. ახალი გარიგების დამატების მოდალი (გადაეცემა lang)
  render_add_trade_modal(lang)

  st.divider()

  if df.empty:
    no_trades_str = t("no_trades_msg", lang) if "no_trades_msg" in t(lang) else ("No trades in the journal yet. Use the button above." if lang == "en" else "ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
    st.info(no_trades_str)
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
    show_more_text = f"⬇️ მეტის ჩვენება ({limit} / {total_count})" if lang == "ka" else f"⬇️ Show More ({limit} / {total_count})"
    if st.button(
        show_more_text,
        use_container_width=True,
        key="journal_show_more",
    ):
      st.session_state["journal_limit"] = limit + PAGE_SIZE
      st.rerun()
