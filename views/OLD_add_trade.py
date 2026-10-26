import os
import uuid
from datetime import datetime
import streamlit as st
from database import insert_trade, upload_screenshot
from utils.translations import t


def render_add_trade_view(lang="ka"):
  st.subheader(
      "➕ ახალი გარიგების / ნაწილობრივი მოქმედების დამატება (Trade Action)"
  )

  with st.form("detailed_trade_form"):
    col1, col2 = st.columns(2)

    with col1:
      entry_date = st.date_input(
          "თარიღი (Entry Date)", datetime(2026, 10, 6)
      )  # საწყისი დეფოლტი თქვენი სასურველი თარიღით
      pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD", key="add_pair")
      side = st.selectbox(
          "მიმართულება (Side)", ["Long", "Short"], key="add_side"
      )
      entry_price = st.number_input(
          "შესვლის ფასი (Entry Price)",
          value=1.0850,
          format="%.5f",
          key="add_entry_price",
      )
      qty = st.number_input(
          "მოცულობა (Qty)", value=6000.0, step=100.0, key="add_qty"
      )
      sl_price = st.number_input(
          "სტოპ ლოსი (SL Price)",
          value=1.0800,
          format="%.5f",
          key="add_sl_price",
      )
      tp_price = st.number_input(
          "ტეიკ პროფიტი (TP Price)",
          value=1.0950,
          format="%.5f",
          key="add_tp_price",
      )

    with col2:
      action_type = st.selectbox(
          "მოქმედების ტიპი (ActionType)",
          [
              "Start Row in Journal (მთავარი შესვლა)",
              "Scale In (დამატება პოზიციაში)",
              "Partial Exit (ნაწილობრივი დახურვა)",
              "Full Exit (სრული დახურვა)",
          ],
          key="add_action_type",
      )
      pattern = st.text_input(
          "პატერნი (Pattern)", "ვ-შემობრუნება", key="add_pattern"
      )
      trigger = st.text_input(
          "ტრიგერი (Trigger)", "ჩამოთვლა / მიწოლა", key="add_trigger"
      )
      trend = st.selectbox(
          "ტრენდი (Trend)", ["მიმდინარე", "კორექცია", "ფლეთი"], key="add_trend"
      )
      risk_reward = st.text_input(
          "რისკის და მოგების თანაფარდობა (R/R)", "1:2", key="add_rr"
      )
      description = st.text_area(
          "აღწერა / კომენტარი (Description)", "", key="add_description"
      )
      trade_screenshot = st.file_uploader(
          "სკრინშოტი (დადარებისთვის)",
          type=["png", "jpg", "jpeg"],
          key="add_trade_screenshot",
      )

    submitted = st.form_submit_button(
        "გარიგების ჩაწერა ბაზაში (Submit Trade)"
    )

    if submitted:
      # სკრინშოტის ატვირთვა უსაფრთხოდ
      screenshot_value = "No Screenshot"
      if trade_screenshot is not None:
        try:
          ext = os.path.splitext(trade_screenshot.name)[1].lower() or ".png"
          stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
          uploaded_url = upload_screenshot(
              trade_screenshot, f"{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
          )
          if uploaded_url:
            screenshot_value = uploaded_url
        except Exception as upload_err:
          st.error(f"სკრინშოტის ატვირთვის შეცდომა: {upload_err}")

      trade_data = {
          "Trade ID": str(uuid.uuid4()),
          "Entry Date": str(entry_date),
          "Pair": pair,
          "Side": side,
          "Entry Price": str(entry_price),
          "Qty": str(qty),
          "SL_Price": str(sl_price),
          "TP_Price": str(tp_price),
          "ActionType": action_type,
          "Pattern": pattern,
          "Trigger": trigger,
          "Trend": trend,
          "Risk_Reward": risk_reward,
          "Description": description,
          "Screenshot": screenshot_value,
          "Finalized": "False",  # მკაცრად უზრუნველყოფს, რომ დეფოლტად არ იყოს დასრულებული
      }

      if insert_trade(trade_data):
        st.success(
            "გარიგების დეტალები წარმატებით შეინახა ბაზაში! (Trade Action"
            " Logged)"
        )
        st.rerun()
      else:
        st.error(
            "მონაცემთა შენახვა ვერ მოხერხდა. შეამოწმეთ ველები ან ბაზის კავშირი."
        )
