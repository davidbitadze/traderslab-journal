import uuid
from datetime import datetime
from database import fetch_trades, insert_trade
import streamlit as st
from views.add_trade_modal import render_add_trade_modal


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  df = fetch_trades()

  # 1. მხოლოდ ახალი მთავარი გარიგების ღილაკი
  render_add_trade_modal()

  st.divider()

  if not df.empty:
    st.subheader("📋 აქტიური და ისტორიული პოზიციები")

    # ვფილტრავთ მხოლოდ მთავარ გარიგებებს (Start Row in Journal)
    main_trades = df[
        df["ActionType"].str.contains("Start Row", case=False, na=False)
    ]

    if main_trades.empty:
      # თუ ActionType ველში ტექსტი სხვაა, უბრალოდ ვიღებთ ყველა უნიკალურ Parent ID-ს
      main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

    # თითოეული მთავარი გარიგებისთვის ვქმნით ვიზუალურ ბარათს
    for index, trade in main_trades.iterrows():
      trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
      pair = trade.get("Pair", "N/A")
      side = trade.get("Side", "N/A")
      entry_date = trade.get("Entry Date", "N/A")
      entry_price = trade.get("Entry Price", "N/A")
      qty = trade.get("Qty", "N/A")
      formation = trade.get("Formation", "N/A")

      # ვიზუალური კონტეინერი თითოეული გარიგებისთვის (ბარათი)
      with st.container(border=True):
        col_info1, col_info2, col_action = st.columns([3, 3, 2])

        with col_info1:
          st.markdown(f"### 💱 {pair} — **{side}**")
          st.caption(
              f"📅 თარიღი: {entry_date} | 🏷️ ფორმაცია: {formation}"
          )

        with col_info2:
          st.write(f"💵 შესვლის ფასი: **{entry_price}**")
          st.write(f"📊 მოცულობა: **{qty}**")

        with col_action:
          # ინდივიდუალური სამართავი მენიუ ამ კონკრეტული გარიგებისთვის
          with st.popover("⚙️ მართვა (...)"):
            st.write(f"**პოზიციის მართვა:** {pair}")

            sub_action_type = st.selectbox(
                "მოქმედება",
                [
                    "Scale In (დამატება / ინვესტირება)",
                    "Partial Exit (ნაწილობრივი ჩახურვა)",
                    "Full Exit (სრული დახურვა)",
                ],
                key=f"act_{trade_id}",
            )

            with st.form(f"form_sub_{trade_id}"):
              sub_price = st.number_input(
                  "ფასი", value=float(entry_price) if str(entry_price).replace('.', '', 1).isdigit() else 1.0850, format="%.5f", key=f"p_{trade_id}"
              )
              sub_qty = st.number_input(
                  "მოცულობა", value=1000.0, step=100.0, key=f"q_{trade_id}"
              )
              sub_date = st.date_input("თარიღი", datetime.today(), key=f"d_{trade_id}")
              sub_desc = st.text_input("შენიშვნა / კომენტარი", key=f"desc_{trade_id}")

              sub_submitted = st.form_submit_button("შესრულება")

              if sub_submitted:
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
                  st.success("მოქმედება წარმატებით დაემატა!")
                  st.rerun()
                else:
                  st.error("ვერ მოხერხდა.")

        # ვეძებთ ამ გარიგებასთან დაკავშირებულ ქვემოქმედებებს (Scale In / Exits)
        sub_actions = df[
            (df["Parent Trade ID"] == trade_id)
            & (
                ~df["ActionType"].str.contains("Start Row", case=False, na=False)
            )
        ]

        if not sub_actions.empty:
          with st.expander(
              f"🔗 დაკავშირებული მოქმედებები ({len(sub_actions)} ეტაპი)"
          ):
            for _, sub in sub_actions.iterrows():
              st.markdown(
                  f"- **{sub.get('ActionType', 'Action')}**: ფასი:"
                  f" {sub.get('Entry Price')} | მოცულობა: {sub.get('Qty')} |"
                  f" თარიღი: {sub.get('Entry Date')}"
              )

  else:
    st.info("ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.")
