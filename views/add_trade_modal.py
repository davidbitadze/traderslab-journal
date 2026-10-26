import os
import uuid
from datetime import datetime
from database import fetch_settings, insert_trade, upload_screenshot
import streamlit as st


def render_add_trade_modal():
  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")

  with st.popover("➕ ახალი გარიგების დამატება"):
    st.subheader("მთავარი გარიგების გახსნა")

    with st.form("new_trade_form"):
      col1, col2 = st.columns(2)

      with col1:
        # დროის ზუსტი მითითებისთვის ვიყენებთ ტექსტურ ველს
        default_time_str = "2026-10-13 16:38:00"
        entry_date = st.text_input(
            "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)", value=default_time_str, key="modal_entry_date"
        )
        pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD", key="modal_pair")
        side = st.selectbox("მიმართულება (Side)", ["Long", "Short"], key="modal_side")
        entry_price = st.number_input(
            "შესვლის ფასი (Price)", value=1.0850, format="%.5f", key="modal_entry_price"
        )
        risk_dollar = st.number_input(
            "რისკი დოლარში (Risk $)", value=10.0, step=1.0, key="modal_risk"
        )
        qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0, key="modal_qty")

      with col2:
        formation = st.selectbox(
            "ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"], key="modal_formation"
        )
        sl_price = st.number_input(
            "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f", key="modal_sl"
        )
        tp_price = st.number_input(
            "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f", key="modal_tp"
        )
        pattern = (
            st.selectbox("პატერნი (Pattern)", patterns_options, key="modal_pattern")
            if patterns_options
            else ""
        )
        trigger = (
            st.selectbox("ტრიგერი (Trigger)", triggers_options, key="modal_trigger")
            if triggers_options
            else ""
        )

      description = st.text_area("აღწერა / კომენტარი (Description)", "", key="modal_desc")
      screenshot = st.file_uploader(
          "გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"], key="modal_screenshot"
      )

      submitted = st.form_submit_button("გარიგების შენახვა (Save Trade)")

      if submitted:
        trade_id = str(uuid.uuid4())
        
        # სკრინშოტის ატვირთვა Supabase-ში
        screenshot_value = "No Screenshot"
        if screenshot is not None:
          try:
            ext = os.path.splitext(screenshot.name)[1].lower() or ".png"
            stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            uploaded_url = upload_screenshot(
                screenshot, f"{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
            )
            if uploaded_url:
              screenshot_value = uploaded_url
          except Exception as upload_err:
            st.error(f"სკრინშოტის ატვირთვის შეცდომა: {upload_err}")

        trade_data = {
            "Trade ID": trade_id,
            "Parent Trade ID": trade_id,
            "Entry Date": str(entry_date),  # ზუსტად თქვენ მიერ ჩწერილი თარიღი წავა ბაზაში!
            "Pair": pair,
            "Side": side,
            "Entry Price": str(entry_price),
            "Qty": str(qty),
            "Risk ($)": str(risk_dollar),
            "SL_Price": str(sl_price),
            "TP_Price": str(tp_price),
            "ActionType": "Start Row in Journal (მთავარი შესვლა)",
            "Pattern": pattern,
            "Trigger": trigger,
            "Formation": formation,
            "Description": description,
            "Screenshot": screenshot_value,
            "Finalized": "False",  # მკაცრად მიმდინარე სტატუსი
        }

        if insert_trade(trade_data):
          st.success("ახალი გარიგება წარმატებით შეიქმნა!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")
