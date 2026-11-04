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

    if "t_side" not in st.session_state:
      st.session_state["t_side"] = "Long"
    if "t_entry" not in st.session_state:
      st.session_state["t_entry"] = 1.00000
    if "t_sl" not in st.session_state:
      st.session_state["t_sl"] = 1.00000
    if "t_tp" not in st.session_state:
      st.session_state["t_tp"] = 1.00000

    default_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry_date = st.text_input("თარიღი და დრო", value=default_time_str)
    pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
    
    entry_price = st.number_input("შესვლის ფასი (Price)", value=st.session_state["t_entry"], format="%.5f", key="t_entry_num")
    qty = st.number_input("მოცულობა (Qty)", value=1000.0, step=100.0)
    risk_dollar = st.number_input("რისკი დოლარში (Risk $)", value=10.0, step=1.0)
    sl_price = st.number_input("სტოპ ლოსი (SL Price)", value=st.session_state["t_sl"], format="%.5f", key="t_sl_num")
    tp_price = st.number_input("ტეიკ პროფიტი (TP Price)", value=st.session_state["t_tp"], format="%.5f", key="t_tp_num")

    # მიმართულება ტეიკ-პროფიტის ქვემოთ
    side = st.radio(
        "მიმართულება (Side)", 
        ["Long", "Short"], 
        index=0 if st.session_state["t_side"] == "Long" else 1, 
        horizontal=True, 
        key="t_side_radio",
        on_change=lambda: st.session_state.update({"t_side": st.session_state["t_side_radio"]})
    )

    st.session_state["t_entry"] = entry_price
    st.session_state["t_sl"] = sl_price
    st.session_state["t_tp"] = tp_price

    # R/R კოეფიციენტის მყისიერი გამოთვლა
    rr_text = "გაანგარიშება..."
    try:
      e_val = float(entry_price)
      s_val = float(sl_price)
      t_val = float(tp_price)

      if side == "Long":
        risk_diff = e_val - s_val
        reward_diff = t_val - e_val
      else:  # Short
        risk_diff = s_val - e_val
        reward_diff = e_val - t_val

      if risk_diff > 0 and reward_diff > 0:
        rr_ratio = reward_diff / risk_diff
        rr_text = f"1:{rr_ratio:.2f} ({rr_ratio:.2f}R)"
      else:
        if side == "Long":
          rr_text = "არასწორი მანძილები: Long-ისთვის (სტოპი < შესვლა < პროფიტი)"
        else:
          rr_text = "არასწორი მანძილები: Short-ისთვის (პროფიტი < შესვლა < სტოპი)"
    except Exception:
      rr_text = "შეიყვანეთ რიცხვითი ფასები"

    st.markdown(
        f"📊 **პოტენციური რისკ-მოგება (R/R):** <span style='color: #22c55e; font-weight: bold;'>{rr_text}</span>", 
        unsafe_allow_html=True
    )
    st.divider()

    pattern = st.selectbox("პატერნი (Pattern)", patterns_options) if patterns_options else ""
    trigger = st.selectbox("ტრიგერი (Trigger)", triggers_options) if triggers_options else ""
    formation = st.selectbox("ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"])

    description = st.text_area("აღწერა / კომენტარი (Description)", "")
    screenshot = st.file_uploader("გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"])

    if st.button("გარიგების შენახვა (Save Trade)", type="primary"):
      trade_id = str(uuid.uuid4())
      
      screenshot_value = "No Screenshot"
      if screenshot is not None:
        try:
          ext = os.path.splitext(screenshot.name)[1].lower() or ".png"
          stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
          file_safe_name = f"{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
          uploaded_url = upload_screenshot(screenshot, file_name=file_safe_name)
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
