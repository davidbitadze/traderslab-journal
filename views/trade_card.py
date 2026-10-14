import uuid
from datetime import datetime
from database import delete_trade, insert_trade, update_trade
import streamlit as st
from utils.formulas import calculate_trade_pnl


def render_trade_card(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  entry_price = trade.get("Entry Price", 0)
  formation = trade.get("Formation", "N/A")
  risk_val = trade.get("Risk (\$)", 5.85)

  is_finalized = trade.get("Finalized", False)
  if isinstance(is_finalized, str):
    is_finalized = is_finalized.lower() == "true"

  sub_actions = df[df["Parent Trade ID"] == trade_id]
  exit_price = entry_price

  exits = sub_actions[
      sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
  ]
  if not exits.empty:
    exit_price = exits.iloc[-1].get("Entry Price", entry_price)

  pnl = calculate_trade_pnl(entry_price, exit_price, risk_val, side)
  status_icon = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")

  with st.container(border=True):
    col_main, col_menu = st.columns([10, 1])

    with col_main:
      st.markdown(
          f"### {status_icon} **{pair}** &nbsp;&nbsp;|&nbsp;&nbsp; `{side}`"
          f" &nbsp;&nbsp; **{pnl:+.2f}\$**"
      )
      st.caption(
          f"📅 {entry_date} &nbsp;&nbsp;•&nbsp;&nbsp; 🏷️ {formation}"
          f" &nbsp;&nbsp;•&nbsp;&nbsp; 💵 შესვლა: {entry_price}"
          f" &nbsp;&nbsp;•&nbsp;&nbsp; სტატუსი:"
          f" {'✅ დასრულებული' if is_finalized else '⏳ აქტიური'}"
      )

    with col_menu:
      with st.popover("⋯"):
        st.subheader(f"მართვა: {pair}")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
          edit_clicked = st.button("✏️ ჩასწორება", key=f"edit_btn_{trade_id}")
        with col_btn2:
          delete_clicked = st.button("🗑️ წაშლა", key=f"del_btn_{trade_id}")

        state_key = f"mode_{trade_id}"
        if edit_clicked:
          st.session_state[state_key] = "edit"
        elif delete_clicked:
          st.session_state[state_key] = "delete"

        current_mode = st.session_state.get(state_key, None)

        st.divider()

        if current_mode == "edit":
          st.write("**პოზიციის მართვა / დამატება / ჩახურვა**")

          sub_action_type = st.selectbox(
              "მოქმედება",
              [
                  "Scale In (დამატება)",
                  "Partial Exit (ნაწილობრივი ჩახურვა)",
                  "Full Exit (სრული ჩახურვა)",
              ],
              key=f"act_{trade_id}",
          )

          with st.form(f"form_sub_{trade_id}"):
            default_sub_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sub_date = st.text_input(
                "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)",
                value=default_sub_time,
                key=f"d_{trade_id}",
            )
            sub_price = st.number_input(
                "ფასი",
                value=float(entry_price)
                if str(entry_price).replace(".", "", 1).isdigit()
                else 1.0850,
                format="%.5f",
                key=f"p_{trade_id}",
            )
            sub_qty = st.number_input(
                "მოცულობა", value=1000.0, step=100.0, key=f"q_{trade_id}"
            )
            sub_desc = st.text_input("შენიშვნა", key=f"desc_{trade_id}")

            # სკრინშოტი ჩახურვისთვის / მოქმედებისთვის
            sub_screenshot = st.file_uploader(
                "მოქმედების სკრინშოტი (დადარებისთვის)",
                type=["png", "jpg", "jpeg"],
                key=f"file_{trade_id}",
            )

            mark_finalized = st.checkbox(
                "გარიგება დასრულებულია (Finalized)",
                value=is_finalized,
                key=f"fin_chk_{trade_id}",
            )

            if st.form_submit_button("ცვლილებების შენახვა"):
              screenshot_name = (
                  sub_screenshot.name if sub_screenshot else "No Screenshot"
              )
              child_trade_data = {
                  "Trade ID": str(uuid.uuid4()),
                  "Parent Trade ID": trade_id,
                  "Entry Date": sub_date,
                  "Pair": pair,
                  "Side": side,
                  "Entry Price": str(sub_price),
                  "Qty": str(sub_qty),
                  "ActionType": sub_action_type,
                  "Description": sub_desc,
                  "Screenshot": screenshot_name,
              }
              update_trade(trade_id, {"Finalized": str(mark_finalized)})

              if insert_trade(child_trade_data):
                st.success("წარმატებით შეინახა!")
                del st.session_state[state_key]
                st.rerun()

        elif current_mode == "delete":
          st.error(
              "⚠️ ნამდვილად გსურთ წაშლა? წაშლის შემდეგ მონაცემები ვეღარ"
              " აღდგება!"
          )

          col_d1, col_d2 = st.columns(2)
          with col_d1:
            if st.button("OK", key=f"conf_del_{trade_id}"):
              if delete_trade(trade_id):
                st.success("წაიშალა!")
                del st.session_state[state_key]
                st.rerun()
          with col_d2:
            if st.button("Cancel", key=f"canc_del_{trade_id}"):
              del st.session_state[state_key]
              st.rerun()

    if not sub_actions.empty:
      with st.expander(f"📋 დეტალური ისტორია ({len(sub_actions)} ქვემოქმედება)"):
        for _, sub in sub_actions.iterrows():
          st.markdown(
              f"- **{sub.get('ActionType')}**: ფასი: {sub.get('Entry Price')}"
              f" | მოცულობა: {sub.get('Qty')} | დრო: {sub.get('Entry Date')}"
              f" | სკრინშოტი: {sub.get('Screenshot', 'არა')}"
          )
