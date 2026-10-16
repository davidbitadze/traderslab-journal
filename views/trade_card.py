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
from utils.formulas import calculate_trade_pnl

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"

CARD_CSS = """
<style>
[data-testid="stImage"] img { border-radius: 10px; object-fit: cover; }
.tc-title { font-size: 1.05rem; line-height: 1.5; }
.tc-thumb {
  width: 76px; height: 56px; border-radius: 10px;
  background: rgba(148,163,184,0.12);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem;
}
</style>
"""


def _to_float(value, default=0.0):
  try:
    if value is None or str(value).strip() in ("", "None", "nan"):
      return default
    return float(value)
  except (ValueError, TypeError):
    return default


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
    return "ზრდა (Long)"
  if s == "short":
    return "კლება (Short)"
  return str(side)


def recalc_net_pnl(parent_id):
  """ითვლის გარიგების Net P/L-ს ბაზის ახალი მონაცემებით და წერს Supabase-ში."""
  df = fetch_trades()
  if df.empty:
    return

  main_df = df[df["Trade ID"] == parent_id]
  if main_df.empty:
    return
  main = main_df.iloc[0]

  side = main.get("Side", "")
  risk_v = _to_float(main.get("Risk ($)"), 5.85)
  subs = df[df["Parent Trade ID"] == parent_id]

  # შესვლა: საწყისი რიგი + Scale In-ები (საშუალო შეწონილი ფასი)
  entry_legs = [(_to_float(main.get("Entry Price")), _to_float(main.get("Qty")))]
  for _, s in subs.iterrows():
    if "Scale In" in str(s.get("ActionType", "")):
      entry_legs.append(
          (_to_float(s.get("Entry Price")), _to_float(s.get("Qty")))
      )

  entry_qty = sum(q for _, q in entry_legs)
  if entry_qty > 0:
    entry_p = sum(p * q for p, q in entry_legs) / entry_qty
  else:
    entry_p = entry_legs[0][0]

  exits = [
      (_to_float(s.get("Entry Price"), entry_p), _to_float(s.get("Qty")))
      for _, s in subs.iterrows()
      if "Exit" in str(s.get("ActionType", ""))
  ]

  if not exits:
    update_trade(parent_id, {"Net P/L": None})
    return

  denom = entry_qty if entry_qty > 0 else sum(q for _, q in exits)

  total_pnl = 0.0
  for ex_p, ex_q in exits:
    share = (ex_q / denom) if denom > 0 else 1.0
    total_pnl += calculate_trade_pnl(entry_p, ex_p, risk_v, side) * share

  update_trade(parent_id, {"Net P/L": str(round(total_pnl, 2))})


# 🪟 Streamlit-ის ოფიციალური ოვერლეი ფანჯარა (Dialog) დეტალებისა და მართვისთვის
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

  st.markdown(f"### {pair} — **{side}**")
  if _is_url(main_screenshot):
    st.image(main_screenshot, use_container_width=True)
  st.divider()

  # 1. არსებული ისტორია წაშლისა და ედიტირების ღილაკებით
  if not sub_actions.empty:
    st.markdown("**📋 ეტაპების ისტორია:**")
    for _, sub in sub_actions.iterrows():
      sub_id = sub.get("Trade ID")
      col_h1, col_h2, col_h3 = st.columns([7, 1, 1])
      with col_h1:
        st.info(
            f"• **{sub.get('ActionType')}** | ფასი: {sub.get('Entry Price')} |"
            f" მოც.: {sub.get('Qty')} | დრო: {sub.get('Entry Date')}"
        )
        if _is_url(sub.get("Screenshot", "")):
          st.image(sub.get("Screenshot"), width=220)
      with col_h2:
        if st.button("✏️", key=f"edit_sub_{sub_id}", help="ამ ეტაპის ჩასწორება"):
          st.session_state["active_edit_sub"] = sub_id
      with col_h3:
        if st.button("🗑️", key=f"del_sub_{sub_id}", help="ამ ეტაპის წაშლა"):
          if delete_trade(sub_id):
            recalc_net_pnl(trade_id)
            st.toast("ჩანაწერი წაიშალა!", icon="🗑️")
            st.rerun(scope="fragment")

      if st.session_state.get("active_edit_sub") == sub_id:
        with st.form(f"form_edit_sub_inline_{sub_id}"):
          st.markdown(f"**✏️ ჩასწორება: {sub.get('ActionType')}**")
          is_start_row = "Start Row" in str(sub.get("ActionType", ""))

          edit_price = st.number_input(
              "ფასი",
              value=_to_float(sub.get("Entry Price"), 1.0850),
              format="%.5f",
          )
          edit_qty = st.number_input(
              "მოცულობა",
              value=_to_float(sub.get("Qty"), 1000.0),
              step=100.0,
          )

          edit_risk = 10.0
          if is_start_row:
            edit_risk = st.number_input(
                "რისკი დოლარში (Risk $)",
                value=_to_float(sub.get("Risk ($)"), 10.0),
                step=1.0,
            )

          edit_date = st.text_input(
              "თარიღი და დრო", value=str(sub.get("Entry Date", ""))
          )

          col_es1, col_es2 = st.columns(2)
          with col_es1:
            if st.form_submit_button("💾 შენახვა", use_container_width=True):
              update_data = {
                  "Entry Price": str(edit_price),
                  "Qty": str(edit_qty),
                  "Entry Date": edit_date,
              }
              if is_start_row:
                update_data["Risk ($)"] = str(edit_risk)

              if update_trade(sub_id, update_data):
                recalc_net_pnl(trade_id)
                st.success("წარმატებით განახლდა!")
                st.session_state["active_edit_sub"] = None
                st.rerun(scope="fragment")

          with col_es2:
            if st.form_submit_button("❌ გაუქმება", use_container_width=True):
              st.session_state["active_edit_sub"] = None
              st.rerun(scope="fragment")

  else:
    st.caption("ამ გარიგებაზე დამატებითი ეტაპები ჯერ არ არის.")

  st.markdown("---")

  # 2. ახალი ეტაპის დამატება
  with st.expander("➕ ახალი ეტაპის დამატება"):
    sub_action_type = st.selectbox(
        "მოქმედების ტიპი",
        [
            "Full Exit (გამოსვლა)",
            "Partial Exit (ნაწილობრივ გამოსვლა)",
            "Scale In (დამატება)",
        ],
        key=f"dialog_act_{trade_id}",
    )

    with st.form(f"form_sub_dialog_{trade_id}"):
      col_f1, col_f2 = st.columns(2)
      with col_f1:
        default_sub_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sub_date = st.text_input(
            "თარიღი და დრო",
            value=default_sub_time,
            key=f"dialog_date_{trade_id}",
        )
        sub_price = st.number_input(
            "ფასი",
            value=_to_float(entry_price, 1.0850),
            format="%.5f",
            key=f"dialog_price_{trade_id}",
        )
      with col_f2:
        sub_qty = st.number_input(
            "მოცულობა", value=1000.0, step=100.0, key=f"dialog_qty_{trade_id}"
        )

      sub_desc = st.text_input(
          "შენიშვნა / კომენტარი", key=f"dialog_desc_{trade_id}"
      )
      sub_screenshot = st.file_uploader(
          "სკრინშოტი (დადარებისთვის)",
          type=["png", "jpg", "jpeg"],
          key=f"dialog_file_{trade_id}",
      )

      col_sub_btn1, col_sub_btn2 = st.columns(2)
      with col_sub_btn1:
        submitted = st.form_submit_button(
            "💾 შენახვა", use_container_width=True
        )
      with col_sub_btn2:
        cancelled = st.form_submit_button(
            "❌ გაუქმება", use_container_width=True
        )
      if cancelled:
        st.rerun(scope="fragment")

      if submitted:
        screenshot_value = "No Screenshot"
        if sub_screenshot is not None:
          try:
            ext = os.path.splitext(sub_screenshot.name)[1].lower() or ".png"
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            uploaded_url = upload_screenshot(
                sub_screenshot, f"{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
            )
            if uploaded_url:
              screenshot_value = uploaded_url
          except Exception as upload_err:
            st.error(f"სკრინშოტის ატვირთვის შეცდომა: {upload_err}")

        child_trade_data = {
            "Trade ID": str(uuid.uuid4()),
            "Parent Trade ID": trade_id,
            "Entry Date": sub_date,  # გამოყენებულია მომხმარებლის მიერ მითითებული თარიღი!
            "Pair": pair,
            "Side": side,
            "Entry Price": str(sub_price),
            "Qty": str(sub_qty),
            "ActionType": sub_action_type,
            "Description": sub_desc,
            "Screenshot": screenshot_value,
        }
        if insert_trade(child_trade_data):
          recalc_net_pnl(trade_id)
          st.success("წარმატებით დაემატა!")
          st.rerun(scope="fragment")


# ქოლბექი ტოიგლის ცვლილებისთვის
def handle_toggle_change(t_id):
  new_val = st.session_state.get(f"toggle_fin_{t_id}", False)
  update_trade(t_id, {"Finalized": str(new_val)})


def render_trade_card(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  entry_price = trade.get("Entry Price", 0)
  formation = trade.get("Formation", "N/A")
  risk_val = trade.get("Risk ($)", 5.85)
  screenshot = trade.get("Screenshot", "No Screenshot")

  # მკაცრი და სწორი Finalized შემოწმება (რომ დეფოლტად True არ გახდეს)
  raw_fin = trade.get("Finalized", False)
  if isinstance(raw_fin, str):
    is_finalized = raw_fin.strip().lower() == "true"
  else:
    is_finalized = bool(raw_fin)

  sub_actions = df[df["Parent Trade ID"] == trade_id]
  exit_price = entry_price

  exits = sub_actions[
      sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
  ]
  if not exits.empty:
    exit_price = exits.iloc[-1].get("Entry Price", entry_price)

  raw_net = trade.get("Net P/L")
  if raw_net is not None and str(raw_net).strip() not in ("", "None", "nan"):
    pnl = float(raw_net)
  else:
    pnl = calculate_trade_pnl(entry_price, exit_price, risk_val, side)

  pnl_color = GREEN if pnl > 0 else (RED if pnl < 0 else GRAY)
  status_dot = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")

  state_key = f"mode_{trade_id}"
  current_mode = st.session_state.get(state_key, None)

  with st.container(border=True):
    col_thumb, col_info, col_toggle, col_btn, col_menu = st.columns(
        [1.1, 5, 2.2, 1.7, 0.7], vertical_alignment="center"
    )

    with col_thumb:
      if _is_url(screenshot):
        st.image(screenshot, width=76)
      else:
        st.markdown('<div class="tc-thumb">📁</div>', unsafe_allow_html=True)

    with col_info:
      st.markdown(
          CARD_CSS
          + f"<div class='tc-title'><b>{pair}</b> {status_dot} &nbsp;"
          f"<b style='color:{pnl_color}'>{pnl:+.2f}$</b></div>",
          unsafe_allow_html=True,
      )
      st.caption(
          f"{_side_label(side)} • {_pretty_date(entry_date)} • 🏷️ {formation}"
          f" • 💵 {entry_price}"
      )

    with col_toggle:
      current_toggle_state = st.session_state.get(
          f"toggle_fin_{trade_id}", is_finalized
      )
      toggle_label = "დასრულებული" if current_toggle_state else "მიმდინარე"

      st.toggle(
          toggle_label,
          value=is_finalized,
          key=f"toggle_fin_{trade_id}",
          on_change=handle_toggle_change,
          args=(trade_id,),
      )

      if current_toggle_state and exits.empty:
        st.toast(
            f"⚠️ {pair} გარიგება დასრულებულია, თუმცა გამოსვლის (Exit) დეტალები"
            " არ არის გაწერილი.",
            icon="ℹ️",
        )

    with col_btn:
      if st.button(
          "დეტალები", key=f"det_menu_{trade_id}", use_container_width=True
      ):
        show_trade_details_dialog(trade, df)

    with col_menu:
      with st.popover("⋯"):
        st.write(f"**მართვა: {pair}**")
        if st.button("🗑️ გარიგების წაშლა", key=f"del_menu_{trade_id}"):
          st.session_state[state_key] = "delete"
          st.rerun()

    if current_mode == "delete":
      st.divider()
      st.error(
          "⚠️ ნამდვილად გსურთ გარიგებისა და მისი ისტორიის წაშლა? მონაცემები"
          " ვეღარ აღდგება!"
      )
      col_d1, col_d2 = st.columns(2)
      with col_d1:
        if st.button(
            "დიახ, წაშლა", key=f"conf_del_{trade_id}", use_container_width=True
        ):
          if delete_trade(trade_id):
            st.success("წაიშალა!")
            del st.session_state[state_key]
            st.rerun()
      with col_d2:
        if st.button(
            "გაუქმება", key=f"canc_del_{trade_id}", use_container_width=True
        ):
          del st.session_state[state_key]
          st.rerun()
