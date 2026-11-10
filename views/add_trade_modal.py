import os
import uuid
from datetime import datetime
from database import fetch_settings, insert_trade, upload_screenshot
import pandas as pd
import streamlit as st
from utils.formulas import calculate_rr, to_float
from utils.translations import t

GREEN = "#22c55e"
RED = "#ef4444"
AMBER = "#f59e0b"

FORMATIONS = ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"]


def _k(name):
  """ველის გასაღები + "თაობის" ნომერი: შენახვის შემდეგ ნომერი იზრდება და ყველა ველი სუფთად იწყება."""
  return f"modal_{name}_{st.session_state.get('modal_gen', 0)}"


def _rr_html(side, entry, sl, tp, risk_usd, lang="ka"):
  """R/R ბარათი: კოეფიციენტი, შედეგი 1$ რისკზე და მთლიანი რისკი/მოგება დოლარებში."""
  r = calculate_rr(side, entry, sl, tp)
  status = r["status"]

  def box(inner):
    title_text = "📊 პოტენციური რისკ-მოგება (R/R)" if lang == "ka" else "📊 Potential Risk/Reward (R/R)"
    return (
        "<div style='border:1px solid rgba(148,163,184,0.35);border-radius:10px;"
        "padding:10px 14px;margin:4px 0 8px 0;'>"
        f"<div style='font-size:0.8rem;opacity:0.7;'>{title_text}</div>"
        f"{inner}</div>"
    )

  def note(text, color=AMBER):
    return box(f"<div style='color:{color};margin-top:4px;'>{text}</div>")

  if status == "bad_side":
    return note("აირჩიე მიმართულება" if lang == "ka" else "Select direction", RED)
  if status == "no_entry":
    return note("შეიყვანე შესვლის ფასი" if lang == "ka" else "Enter entry price")
  if status == "no_sl_tp":
    return note("შეიყვანე სტოპ ლოსი და ტეიკ პროფიტი" if lang == "ka" else "Enter Stop Loss and Take Profit")
  if status == "bad_sl":
    where = "ქვემოთ" if side == "Long" else "ზემოთ"
    if lang == "en":
      where = "below" if side == "Long" else "above"
      return note(f"Stop Loss for {side} must be {where} entry price", RED)
    return note(f"{side}-ზე სტოპი უნდა იყოს შესვლის ფასის {where}", RED)
  if status == "bad_tp":
    where = "ზემოთ" if side == "Long" else "ქვემოთ"
    if lang == "en":
      where = "above" if side == "Long" else "below"
      return note(f"Take Profit for {side} must be {where} entry price", RED)
    return note(f"{side}-ზე ტეიკ პროფიტი უნდა იყოს შესვლის ფასის {where}", RED)

  risk_usd = to_float(risk_usd)
  parts = []
  if status == "ok":
    rr = r["rr"]
    color = GREEN if rr >= 1 else AMBER
    profit_text = f"1$ risk → <b style='color:{color};'>{rr:.2f}$</b> profit" if lang == "en" else f"1$ რისკზე → <b style='color:{color};'>{rr:.2f}$</b> მოგება"
    parts.append(
        f"<div style='font-size:1.7rem;font-weight:700;color:{color};'>1 : {rr:.2f}</div>"
        f"<div>{profit_text}</div>"
    )
    if risk_usd > 0:
      sl_label = "At SL:" if lang == "en" else "SL-ზე:"
      tp_label = "At TP:" if lang == "en" else "TP-ზე:"
      parts.append(
          "<div style='opacity:0.9;'>"
          f"{sl_label} <b style='color:{RED};'>-{risk_usd:.2f}$</b> &nbsp;·&nbsp; "
          f"{tp_label} <b style='color:{GREEN};'>+{risk_usd * rr:.2f}$</b></div>"
      )
    if rr < 1:
      low_rr_text = "Reward is less than risk" if lang == "en" else "მოგება რისკზე ნაკლებია"
      parts.append(
          f"<div style='color:{AMBER};font-size:0.85rem;'>{low_rr_text}</div>"
      )
  elif status == "no_tp":
    msg = "Take Profit not specified: R/R cannot be calculated" if lang == "en" else "ტეიკ პროფიტი არ არის მითითებული: R/R ვერ გამოითვლება"
    parts.append(f"<div style='color:{AMBER};margin-top:4px;'>{msg}</div>")
  elif status == "no_sl":
    msg = "Stop Loss not specified: R/R cannot be calculated" if lang == "en" else "სტოპ ლოსი არ არის მითითებული: R/R ვერ გამოითვლება"
    parts.append(f"<div style='color:{AMBER};margin-top:4px;'>{msg}</div>")

  return box("".join(parts))


def render_add_trade_modal(lang="ka"):
  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")
  _trade_form(patterns_options, triggers_options, lang)


@st.fragment
def _trade_form(patterns_options, triggers_options, lang="ka"):
  btn_label = "➕ Add New Trade" if lang == "en" else "➕ ახალი გარიგების დამატება"
  
  with st.popover(btn_label, use_container_width=True):
    title_text = "Open Main Trade" if lang == "en" else "მთავარი გარიგების გახსნა"
    st.subheader(title_text)

    date_label = "Date & Time (e.g: 2026-10-13 16:38:00)" if lang == "en" else "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)"
    entry_date = st.text_input(
        date_label,
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        key=_k("date"),
    )
    parsed_date = pd.to_datetime(entry_date, errors="coerce") if entry_date.strip() else pd.NaT
    if pd.isna(parsed_date):
      warn_date = "⚠️ Date could not be parsed." if lang == "en" else "⚠️ თარიღი ვერ იკითხება."
      st.caption(warn_date)
    else:
      ok_date = f"✅ Parsed as: {parsed_date.strftime('%d %b %Y, %H:%M:%S')}" if lang == "en" else f"✅ წაიკითხება როგორც: {parsed_date.strftime('%d %b %Y, %H:%M:%S')}"
      st.caption(ok_date)

    pair = st.text_input("Currency Pair (Pair)" if lang == "en" else "ვალუტის წყვილი (Pair)", "EURUSD", key=_k("pair"))
    entry_price = st.number_input(
        "Entry Price" if lang == "en" else "შესვლის ფასი (Price)", value=0.0, format="%.5f", key=_k("entry")
    )
    qty = st.number_input("Volume (Qty)" if lang == "en" else "მოცულობა (Qty)", value=1000.0, step=100.0, key=_k("qty"))
    risk_dollar = st.number_input(
        "Risk in USD (Risk $)" if lang == "en" else "რისკი დოლარში (Risk $)", value=10.0, step=1.0, key=_k("risk")
    )
    sl_price = st.number_input(
        "Stop Loss (SL Price)" if lang == "en" else "სტოპ ლოსი (SL Price)", value=0.0, format="%.5f", key=_k("sl")
    )
    tp_price = st.number_input(
        "Take Profit (TP Price)" if lang == "en" else "ტეიკ პროფიტი (TP Price)", value=0.0, format="%.5f", key=_k("tp")
    )
    side = st.selectbox("Direction (Side)" if lang == "en" else "მიმართულება (Side)", ["Long", "Short"], key=_k("side"))

    st.markdown(
        _rr_html(side, entry_price, sl_price, tp_price, risk_dollar, lang),
        unsafe_allow_html=True,
    )

    pattern = (
        st.selectbox("Pattern" if lang == "en" else "პატერნი (Pattern)", patterns_options, key=_k("pattern"))
        if patterns_options
        else ""
    )
    trigger = (
        st.selectbox("Trigger" if lang == "en" else "ტრიგერი (Trigger)", triggers_options, key=_k("trigger"))
        if triggers_options
        else ""
    )
    formation = st.selectbox("Formation" if lang == "en" else "ფორმაცია (Formation)", FORMATIONS, key=_k("formation"))
    description = st.text_area("Description / Comment" if lang == "en" else "აღწერა / კომენტარი (Description)", "", key=_k("desc"))
    screenshot = st.file_uploader(
        "Trade Screenshot" if lang == "en" else "გარიგების სკრინშოტი (Screenshot)",
        type=["png", "jpg", "jpeg"],
        key=_k("shot"),
    )

    save_btn_text = "Save Trade" if lang == "en" else "გარიგების შენახვა (Save Trade)"
    if st.button(save_btn_text, type="primary", key=_k("save")):
      errors = []
      if pd.isna(parsed_date):
        errors.append("Invalid date" if lang == "en" else "თარიღი ვერ იკითხება")
      if to_float(entry_price) <= 0:
        errors.append("Enter entry price" if lang == "en" else "შეიყვანე შესვლის ფასი")
      rr_state = calculate_rr(side, entry_price, sl_price, tp_price)["status"]
      if rr_state == "bad_sl":
        errors.append("Stop Loss on wrong side" if lang == "en" else "სტოპი არასწორ მხარესაა")
      if rr_state == "bad_tp":
        errors.append("Take Profit on wrong side" if lang == "en" else "ტეიკ პროფიტი არასწორ მხარესაა")
      if errors:
        prefix = "Not saved: " if lang == "en" else "არ შეინახა: "
        st.error(prefix + "; ".join(errors) + ".")
        return

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
          err_msg = f"Screenshot upload error: {upload_err}" if lang == "en" else f"სკრინშოტის ატვირთვის შეცდომა: {upload_err}"
          st.error(err_msg)

      trade_data = {
          "Trade ID": trade_id,
          "Parent Trade ID": trade_id,
          "Entry Date": parsed_date.strftime("%Y-%m-%d %H:%M:%S"),
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
        toast_msg = "New trade successfully created!" if lang == "en" else "ახალი გარიგება წარმატებით შეიქმნა!"
        st.toast(toast_msg, icon="✅")
        st.session_state["modal_gen"] = st.session_state.get("modal_gen", 0) + 1
        st.rerun()
      else:
        err_save = "Failed to save." if lang == "en" else "შენახვა ვერ მოხერხდა."
        st.error(err_save)
