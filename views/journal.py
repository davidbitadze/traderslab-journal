from datetime import datetime
from database import fetch_trades, insert_trade
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
    # მთავარი გარიგებების ფილტრაცია
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]
    if main_trades.empty:
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    # მთლიანი ბალანსის/ჯამის გამოთვლა ზემოთ (როგორც Glide-შია)
    total_pnl = 0.0

    for index, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      pair = trade.get("Pair", "N/A")
      side = trade.get("Side", "N/A")
      entry_date = trade.get("Entry Date", "N/A")
      entry_price = trade.get("Entry Price", 0)
      qty = trade.get("Qty", "N/A")
      formation = trade.get("Formation", "N/A")
      risk_val = trade.get("Risk (\$)", 5.85)  # რისკის დოლარი ბაზიდან

      # ვძებნით ამ გარიგების ბოლო გასვლის ფასს (თუ არსებობს Exit მოქმედება)
      sub_actions = df[df["Parent Trade ID"] == trade_id]
      exit_price = entry_price  # დეფოლტად თუ არ არის დახურული

      exits = sub_actions[
          sub_actions["ActionType"].str.contains("Exit", case=False, na=False)
      ]
      if not exits.empty:
        exit_price = exits.iloc[-1].get("Entry Price", entry_price)

      # ვიანგარიშებთ შედეგს ფორმულების მოდულიდან
      pnl = calculate_trade_pnl(entry_price, exit_price, risk_val, side)
      total_pnl += pnl

      # ფერადი წრე შედეგის მიხედვით (🟢 მოგება / 🔴 წაგება / ⚪ ღია)
      status_icon = "🟢" if pnl > 0 else ("🔴" if pnl < 0 else "⚪")

      # კომპაქტური ბარათის ვიზუალი (Glide სტილში)
      with st.container(border=True):
        col_main, col_menu = st.columns([10, 1])

        with col_main:
          # ერთიანი კომპაქტური ხაზი: წრე + წყვილი + მიმართულება + შედეგი
          st.markdown(
              f"### {status_icon} **{pair}** &nbsp;&nbsp;|&nbsp;&nbsp; `{side}`"
              f" &nbsp;&nbsp; **{pnl:+.2f}\$**"
          )
          st.caption(
              f"📅 {entry_date} &nbsp;&nbsp;•&nbsp;&nbsp; 🏷️ {formation}"
              f" &nbsp;&nbsp;•&nbsp;&nbsp; 💵 შესვლა: {entry_price}"
          )

        with col_menu:
          # ინდივიდუალური მართვის სამწტილიანი მენიუ
          with st.popover("⋯"):
            st.write(f"**პოზიციის მართვა:** {pair}")

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

  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის.")
