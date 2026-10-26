import os
import uuid
from datetime import datetime
from database import (
    delete_trade,
    insert_trade,
    update_trade,
    fetch_trades,
    upload_screenshot,
)
import pandas as pd
import streamlit as st
from utils.formulas import calculate_net_pnl, to_float

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"
ORANGE = "#f97316"

CARD_CSS = """
<style>
/* ვკრძალავთ სვეტების ჩამოშლას მობილურში და ვინარჩუნებთ ერთიან ჰორიზონტალურ ზოლს */
[data-testid="stHorizontalBlock"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    flex-wrap: nowrap !important;
    background-color: rgba(255, 255, 255, 0.02) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 6px !important;
    padding: 4px 8px !important;
    margin-bottom: 3px !important;
    gap: 6px !important;
    width: 100% !important;
}
[data-testid="stColumn"] {
    width: auto !important;
    flex: unset !important;
    min-width: 0 !important;
}
.trade-thumb {
    width: 34px;
    height: 34px;
    border-radius: 6px;
    object-fit: cover;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
}
div[data-testid="stPopoverBody"] {
    z-index: 99999 !important;
}
</style>
"""

def _has_value(value):
  return value is not None and str(value).strip() not in (
      "", "None", "nan", "NaT", "<NA>"
  )

def _is_url(value):
  return str(value).startswith("http")

def _pretty_date(value):
  try:
    return pd.to_datetime(value).strftime("%d %b %Y, %H:%M")
  except Exception:
    return str(value)

def _side_label(side):
  s = str(side).strip().lower()
  if s == "long":
    return "Long"
  if s == "short":
    return "Short"
  return str(side)

def recalc_net_pnl(parent_id):
  df = fetch_trades()
  if df.empty:
    return
  main_df = df[df["Trade ID"] == parent_id]
  if main_df.empty:
    return
  subs = df[df["Parent Trade ID"] == parent_id]
  net = calculate_net_pnl(main_df.iloc[0], subs)
  update_trade(parent_id, {"Net P/L": None if net is None else str(net)})

@st.dialog("🔍 გარიგების დეტალები და მართვა", width="large")
def show_trade_details_dialog(trade, df):
  df = fetch_trades()
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

  fresh = df[df["Trade ID"] == trade_id]
  if not fresh.empty:
    trade = fresh.iloc[0].to_dict()

  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_price = trade.get("Entry Price", 0)
  main_screenshot = trade.get("Screenshot", "No Screenshot")
  sub_actions = df[df["Parent Trade ID"] == trade_id]

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  st.markdown(f"### {pair} — **{side}**")
  
  col_st1, col_st2, col_st3 = st.columns([2.5, 2.5, 2], vertical_alignment="center")
  with col_st1:
    new_status = st.toggle(
        "დასრულებული" if is_finalized else "მიმდინარე",
        value=is_finalized,
        key=f"dialog_toggle_fin_{trade_id}"
    )
    if new_status != is_finalized:
      update_trade(trade_id, {"Finalized": str(new_status)})
      st.toast("სტატუსი განახლდა!", icon="🔄")
      st.rerun(scope="fragment")

  with col_st2:
    status_badge = "🏁 დასრულებული" if is_finalized else "⚡ მიმდინარე"
    badge_color = GRAY if is_finalized else ORANGE
    st.markdown(f"სტატუსი: <b style='color:{badge_color}'>{status_badge}</b>", unsafe_allow_html=True)

  with col_st3:
    if st.button("🗑️ გარიგების წაშლა", key=f"dlg_del_{trade_id}", use_container_width=True):
      if delete_trade(trade_id):
        st.success("გარიგება წაიშალა!")
        st.rerun()

  st.divider()

  if _is_url(main_screenshot):
    st.image(main_screenshot, use_container_width=True)
  st.divider()

  td_current = trade.get("Entry Date")
  td_text = st.text_input(
      "🗓️ გარიგების თარიღი და დრო",
      value=str(td_current) if _has_value(td_current) else "",
      placeholder="YYYY-MM-DD HH:MM:SS",
      key=f"td_text_{trade_id}",
  )
  td_parsed = pd.to_datetime(td_text, errors="coerce") if td_text.strip() else pd.NaT
  td_invalid = bool(pd.isna(td_parsed))

  col_td1, col_td2 = st.columns([4, 2], vertical_alignment="center")
  with col_td1:
    if td_invalid:
      st.caption("⚠️ თარიღი ვერ იკითხება.")
    else:
      st.caption(f"✅ წაიკითხება როგორც: {td_parsed.strftime('%d %b %Y, %H:%M:%S')}")
  with col_td2:
    if st.button("💾 შენახვა", key=f"td_save_{trade_id}", use_container_width=True, disabled=td_invalid):
      stamp = td_parsed.strftime("%Y-%m-%d %H:%M:%S")
      if update_trade(trade_id, {"Entry Date": stamp}):
        st.toast("თარიღი შენახულია!", icon="🗓️")
        st.rerun(scope="fragment")

  st.divider()

  if not sub_actions.empty:
    st.markdown("**📋 ეტაპების ისტორია:**")
    for _, sub in sub_actions.iterrows():
      sub_id = sub.get("Trade ID")
      col_h1, col_h2, col_h3 = st.columns([7, 1, 1])
      with col_h1:
        st.info(f"• **{sub.get('ActionType')}** | ფასი: {sub.get('Entry Price')} | მოც.: {sub.get('Qty')}")
      with col_h2:
        if st.button("✏️", key=f"edit_sub_{sub_id}"):
          st.session_state["active_edit_sub"] = sub_id
      with col_h3:
        if st.button("🗑️", key=f"del_sub_{sub_id}"):
          if delete_trade(sub_id):
            recalc_net_pnl(trade_id)
            st.rerun(scope="fragment")
  else:
    st.caption("დამატებითი ეტაპები არ არის.")

  st.divider()
  if st.button("✅ დახურვა", key=f"close_dlg_{trade_id}", use_container_width=True):
    st.rerun()

def render_trade_card(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  screenshot = trade.get("Screenshot", "No Screenshot")

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  sub_actions = df[df["Parent Trade ID"] == trade_id]
  raw_net = trade.get("Net P/L")
  if _has_value(raw_net):
    pnl = to_float(raw_net)
  else:
    pnl = calculate_net_pnl(trade, sub_actions) or 0.0

  state_key = f"mode_{trade_id}"
  current_mode = st.session_state.get(state_key, None)

  st.markdown(CARD_CSS, unsafe_allow_html=True)

  if is_finalized:
    pnl_color = GREEN if pnl > 0 else (RED if pnl < 0 else GRAY)
    status_indicator = f"<span style='color:{pnl_color}; font-weight:600;'>{pnl:+.2f}$</span>"
  else:
    status_indicator = f"<span style='background-color: {ORANGE}; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight: 500;'>მიმდინარე</span>"

  thumb_html = f"<img src='{screenshot}' class='trade-thumb'>" if _is_url(screenshot) else "<div class='trade-thumb'>📁</div>"

  # სვეტები მკაცრად ფიქსირდება ერთ ხაზზე როგორც კომპიუტერში, ისე მობილურში
  col_thumb, col_info, col_menu = st.columns([0.7, 8.8, 0.5], vertical_alignment="center")

  with col_thumb:
    st.markdown(thumb_html, unsafe_allow_html=True)

  with col_info:
    st.markdown(
        f"""
        <div style='display: flex; flex-direction: column; justify-content: center; min-width: 0;'>
            <div style='font-size: 0.86rem; font-weight: 600; color: #ffffff; display: flex; align-items: center; gap: 6px; line-height: 1.1;'>
                <span>{pair}</span>
                {status_indicator}
            </div>
            <div style='font-size: 0.7rem; color: #94a3b8; margin-top: 1px; display: flex; align-items: center; gap: 4px;'>
                <span>{_side_label(side)}</span>
                <span>•</span>
                <span>{_pretty_date(entry_date)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

  with col_menu:
    with st.popover("⋯"):
      if st.button("📄 დეტალები", key=f"det_menu_{trade_id}", use_container_width=True):
        show_trade_details_dialog(trade, df)
      
      if st.button("🗑️ წაშლა", key=f"del_menu_{trade_id}", use_container_width=True):
        st.session_state[state_key] = "delete"
        st.rerun()

  if current_mode == "delete":
    st.error("⚠️ ნამდვილად გსურთ გარიგების წაშლა?")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
      if st.button("დიახ", key=f"conf_del_{trade_id}", use_container_width=True):
        if delete_trade(trade_id):
          st.success("წაიშალა!")
          del st.session_state[state_key]
          st.rerun()
    with col_d2:
      if st.button("გაუქმება", key=f"canc_del_{trade_id}", use_container_width=True):
        del st.session_state[state_key]
        st.rerun()
