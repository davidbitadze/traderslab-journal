import uuid
from datetime import datetime
from database import fetch_settings, insert_trade
import streamlit as st


def render_add_trade_modal():
  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")

  with st.popover("➕ ახალი გარიგების დამატება"):
    st.subheader("მთავარი გარიგების გახსნა")

    with st.form("new_trade_form"):
      col1, col2 = st.columns(2)

      with col1:
        # დროის კოპირებისთვის ვიყენებთ text_input-ს, რომ ჩასვათ ზუსტი ფორმატით (მაგ: 2026-10-13 16:38:00)
        default_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry_date = st.text_input(
            "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)", value=default_time_str
        )
        pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
        side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
        entry_price = st.number_input(
            "შესვლის ფასი (Price)", value=1.0850, format="%.5f"
        )
        risk_dollar = st.number_input(
            "რისკი დოლარში (Risk $)", value=10.0, step=1.0
        )
        qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0)

      with col2:
        formation = st.selectbox(
            "ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"]
        )
        sl_price = st.number_input(
            "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f"
        )
        tp_price = st.number_input(
            "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f"
        )
        pattern = (
            st.selectbox("პატერნი (Pattern)", patterns_options)
            if patterns_options
            else ""
        )
        trigger = (
            st.selectbox("ტრიგერი (Trigger)", triggers_options)
            if triggers_options
            else ""
        )

      description = st.text_area("აღწერა / კომენტარი (Description)", "")
      screenshot = st.file_uploader(
          "გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"]
      )

      submitted = st.form_submit_button("გარიგების შენახვა (Save Trade)")

      if submitted:
        trade_id = str(uuid.uuid4())
        screenshot_name = screenshot.name if screenshot else "No Screenshot"

        trade_data = {
            "Trade ID": trade_id,
            "Parent Trade ID": trade_id,
            "Entry Date": entry_date,
            "Pair": pair,
            "Side": side,
            "Entry Price": str(entry_price),
            "Qty": str(qty),
            "SL_Price": str(sl_price),
            "TP_Price": str(tp_price),
            "ActionType": "Start Row in Journal (მთავარი შესვლა)",
            "Pattern": pattern,
            "Trigger": trigger,
            "Formation": formation,
            "Description": description,
            "Screenshot": screenshot_name,
        }

        if insert_trade(trade_data):
          st.success("ახალი გარიგება წარმატებით შეიქმნა!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")
