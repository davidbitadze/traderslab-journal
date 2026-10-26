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
        # 1. თარიღი და დრო
        default_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry_date = st.text_input(
            "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)", 
            value=default_time_str, 
            key="modal_entry_date"
        )
        # 2. ვალუტის წყვილი
        pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD", key="modal_pair")
        # 3. შესვლის ფასი
        entry_price = st.number_input(
            "შესვლის ფასი (Price)", value=1.0850, format="%.5f", key="modal_entry_price"
        )
        # 4. მოცულობა
        qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0, key="modal_qty")
        # 5. რისკი დოლარში
        risk_dollar = st.number_input(
            "რისკი დოლარში (Risk $)", value=10.0, step=1.0, key="modal_risk"
        )
        # 6. სტოპ ლოსი
        sl_price = st.number_input(
            "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f", key="modal_sl"
        )
        # 7. ტეიკ პროფიტი
        tp_price = st.number_input(
            "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f", key="modal_tp"
        )

      with col2:
        # 8. პატერნი
        pattern = (
            st.selectbox("პატერნი (Pattern)", patterns_options, key="modal_pattern")
            if patterns_options
            else ""
        )
        # 9. ტრიგერი
        trigger = (
            st.selectbox("ტრიგერი (Trigger)", triggers_options, key="modal_trigger")
            if triggers_options
            else ""
        )
        # 10. მიმართულება
        side = st.selectbox("მიმართულება (Side)", ["Long", "Short"], key="modal_side")
        # 11. ფორმაცია
        formation = st.selectbox(
            "ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"], key="modal_formation"
        )

      # 12. აღწერა / კომენტარი
      description = st.text_area("აღწერა / კომენტარი (Description)", "", key="modal_desc")
      
      # 13. გარიგების სკრინშოტი
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
            "Entry Date": str(entry_date),
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
            "Finalized": "False",
        }

        if insert_trade(trade_data):
          st.success("ახალი გარიგება წარმატებით შეიქმნა!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")
