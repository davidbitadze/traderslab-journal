import uuid
from datetime import datetime
from database import delete_trade, fetch_trades, insert_trade, update_trade
import streamlit as st
from utils.formulas import calculate_trade_pnl
from views.add_trade_modal import render_add_trade_modal


def render_journal_view(lang="ka"):
  st.title("📊 სავაჭრო ჟურნალი (Trading Journal)")

  df = fetch_trades()

  # მთავარი გარიგების დამატების ღილაკი
  render_add_trade_modal()

  st.divider()

  if not df.empty:
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    for index, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      pair = trade.get("Pair", "N/A")
      side = trade.get("Side", "N/A")
      entry_date = trade.get("Entry Date", "N/A")
      entry_price = trade.get("Entry Price", 0)
      formation = trade.get("Formation", "N/A")
      risk_val = trade.get("Risk (\$)", 5.85)

      # სტატუსის შემოწმება (Finalized / დასრულებული)
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
      status_icon = (
          "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")
      )  # ფერადი წრე

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
          # მართვის სამწტილიანი მენიუ (Glide სტილში)
          with st.popover("⋯"):
            st.write(f"**პოზიციის მართვა:** {pair}")

            menu_action = st.selectbox(
                "არჩევანი",
                [
                    "პოზიციის მართვა (Scale In/Exit)",
                    "სტატუსის შეცვლა (Finalized)",
                    "🗑️ გარიგების წაშლა",
                ],
                key=f"menu_{trade_id}",
            )

            if "მართვა" in menu_action:
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
                sub_date = st.date_input(
                    "თარიღი", datetime.today(), key=f"d_{trade_id}"
                )
                sub_desc = st.text_input("შენიშვნა", key=f"desc_{trade_id}")

                if st.form_submit_button("შესრულება"):
                  child_trade_data = {
                      "Trade ID": str(uuid.uuid4()),
                      "Parent Trade ID": trade_id,
                      "Entry Date": str(sub_date),
                      "Pair": pair,
                      "Side": side,
                      "Entry Price": str(sub_price),
                      "Qty": str(sub_qty),
                      "ActionType": sub_action_type,
                      "Description": sub_desc,
                  }
                  if insert_trade(child_trade_data):
                    st.success("მოქმედება დაემატა!")
                    st.rerun()

            elif "სტატუსის" in menu_action:
              new_status = st.checkbox(
                  "გარიგება დასრულებულია (Finalized)",
                  value=is_finalized,
                  key=f"chk_{trade_id}",
              )
              if st.button("სტატუსის შენახვა", key=f"btn_stat_{trade_id}"):
                if update_trade(trade_id, {"Finalized": str(new_status)}):
                  st.success("სტატუსი განახლდა!")
                  st.rerun()

            elif "წაშლა" in menu_action:
              st.warning(
                  "ნამდვილად გსურთ ამ გარიგებისა და მისი ისტორიის წაშლა?"
              )
              if st.button("⚠️ დიახ, წაშლა", key=f"del_{trade_id}"):
                if delete_trade(trade_id):
                  st.success("გარიგება წაიშალა!")
                  st.rerun()
                else:
                  st.error("წაშლა ვერ მოხერხდა.")

        # ჩაშლილი ისტორია / დაკავშირებული მოქმედებები
        if not sub_actions.empty:
          with st.expander(
              f"📋 დეტალური ისტორია ({len(sub_actions)} ქვემოქმედება)"
          ):
            for _, sub in sub_actions.iterrows():
              st.markdown(
                  f"- **{sub.get('ActionType')}**: ფასი: {sub.get('Entry Price')}"
                  f" | მოცულობა: {sub.get('Qty')} | თარიღი:"
                  f" {sub.get('Entry Date')}"
              )

  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის.")
