import os
import uuid
from datetime import datetime
from database import fetch_settings, insert_trade, upload_screenshot
import pandas as pd
import streamlit as st
from utils.formulas import calculate_rr, to_float

GREEN = "#22c55e"
RED = "#ef4444"
AMBER = "#f59e0b"

FORMATIONS = ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"]


def _k(name):
  """ველის გასაღები + "თაობის" ნომერი: შენახვის შემდეგ ნომერი იზრდება და ყველა ველი სუფთად იწყება."""
  return f"modal_{name}_{st.session_state.get('modal_gen', 0)}"


def _rr_html(side, entry, sl, tp, risk_usd):
  """R/R ბარათი: კოეფიციენტი, შედეგი 1$ რისკზე და მთლიანი რისკი/მოგება დოლარებში."""
  r = calculate_rr(side, entry, sl, tp)
  status = r["status"]

  def box(inner):
    return (
        "<div style='border:1px solid rgba(148,163,184,0.35);border-radius:10px;"
        "padding:10px 14px;margin:4px 0 8px 0;'>"
        "<div style='font-size:0.8rem;opacity:0.7;'>📊 პოტენციური რისკ-მოგება (R/R)</div>"
        f"{inner}</div>"
    )

  def note(text, color=AMBER):
    return box(f"<div style='color:{color};margin-top:4px;'>{text}</div>")

  if status == "bad_side":
    return note("აირჩიე მიმართულება", RED)
  if status == "no_entry":
    return note("შეიყვანე შესვლის ფასი")
  if status == "no_sl_tp":
    return note("შეიყვანე სტოპ ლოსი და ტეიკ პროფიტი")
  if status == "bad_sl":
    where = "ქვემოთ" if side == "Long" else "ზემოთ"
    return note(f"{side}-ზე სტოპი უნდა იყოს შესვლის ფასის {where}", RED)
  if status == "bad_tp":
    where = "ზემოთ" if side == "Long" else "ქვემოთ"
    return note(f"{side}-ზე ტეიკ პროფიტი უნდა იყოს შესვლის ფასის {where}", RED)

  risk_usd = to_float(risk_usd)
  parts = []
  if status == "ok":
    rr = r["rr"]
    color = GREEN if rr >= 1 else AMBER
    parts.append(
        f"<div style='font-size:1.7rem;font-weight:700;color:{color};'>1 : {rr:.2f}</div>"
        f"<div>1$ რისკზე → <b style='color:{color};'>{rr:.2f}$</b> მოგება</div>"
    )
    if risk_usd > 0:
      parts.append(
          "<div style='opacity:0.9;'>"
          f"SL-ზე: <b style='color:{RED};'>-{risk_usd:.2f}$</b> &nbsp;·&nbsp; "
          f"TP-ზე: <b style='color:{GREEN};'>+{risk_usd * rr:.2f}$</b></div>"
      )
    if rr < 1:
      parts.append(
          f"<div style='color:{AMBER};font-size:0.85rem;'>მოგება რისკზე ნაკლებია</div>"
      )
  elif status == "no_tp":
    parts.append(
        f"<div style='color:{AMBER};margin-top:4px;'>ტეიკ პროფიტი არ არის მითითებული:"
        " R/R ვერ გამოითვლება</div>"
    )
  elif status == "no_sl":
    parts.append(
        f"<div style='color:{AMBER};margin-top:4px;'>სტოპ ლოსი არ არის მითითებული:"
        " R/R ვერ გამოითვლება</div>"
    )

  dist = []
  if r["risk_dist"] is not None:
    dist.append(f"SL მანძილი: {r['risk_dist']:.5f}")
  if r["reward_dist"] is not None:
    dist.append(f"TP მანძილი: {r['reward_dist']:.5f}")
  if dist:
    parts.append(
        f"<div style='opacity:0.6;font-size:0.8rem;'>{' · '.join(dist)}</div>"
    )
  if r["sl_too_far"]:
    parts.append(
        f"<div style='color:{AMBER};font-size:0.85rem;'>⚠️ SL შესვლიდან 8%-ზე შორსაა:"
        " Net P/L ძველი %-ის ფორმულით დაითვლება</div>"
    )
  return box("".join(parts))


def render_add_trade_modal():
  # ბაზიდან სიები ერთხელ იკითხება და ფრაგმენტს გადაეცემა: ფასის შეცვლისას ბაზას აღარ ვეკითხებით
  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")
  _trade_form(patterns_options, triggers_options)


@st.fragment
def _trade_form(patterns_options, triggers_options):
  with st.popover("➕ ახალი გარიგების დამატება"):
    st.subheader("მთავარი გარიგების გახსნა")

    entry_date = st.text_input(
        "თარიღი და დრო (მაგ: 2026-10-13 16:38:00)",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        key=_k("date"),
    )
    parsed_date = pd.to_datetime(entry_date, errors="coerce") if entry_date.strip() else pd.NaT
    if pd.isna(parsed_date):
      st.caption("⚠️ თარიღი ვერ იკითხება. მაგალითი: 2026-10-13 16:38:00")
    else:
      st.caption(f"✅ წაიკითხება როგორც: {parsed_date.strftime('%d %b %Y, %H:%M:%S')}")

    pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD", key=_k("pair"))
    entry_price = st.number_input(
        "შესვლის ფასი (Price)", value=0.0, format="%.5f", key=_k("entry")
    )
    qty = st.number_input("მოცულობა (Qty)", value=1000.0, step=100.0, key=_k("qty"))
    risk_dollar = st.number_input(
        "რისკი დოლარში (Risk $)", value=10.0, step=1.0, key=_k("risk")
    )
    sl_price = st.number_input(
        "სტოპ ლოსი (SL Price)", value=0.0, format="%.5f", key=_k("sl")
    )
    tp_price = st.number_input(
        "ტეიკ პროფიტი (TP Price)", value=0.0, format="%.5f", key=_k("tp")
    )
    side = st.selectbox("მიმართულება (Side)", ["Long", "Short"], key=_k("side"))

    # R/R: ფრაგმენტი მხოლოდ ამ ფორმას ანახლებს, ამიტომ შედეგი ციფრის შეცვლისთანავე ჩანს
    st.markdown(
        _rr_html(side, entry_price, sl_price, tp_price, risk_dollar),
        unsafe_allow_html=True,
    )

    pattern = (
        st.selectbox("პატერნი (Pattern)", patterns_options, key=_k("pattern"))
        if patterns_options
        else ""
    )
    trigger = (
        st.selectbox("ტრიგერი (Trigger)", triggers_options, key=_k("trigger"))
        if triggers_options
        else ""
    )
    formation = st.selectbox("ფორმაცია (Formation)", FORMATIONS, key=_k("formation"))
    description = st.text_area("აღწერა / კომენტარი (Description)", "", key=_k("desc"))
    screenshot = st.file_uploader(
        "გარიგების სკრინშოტი (Screenshot)",
        type=["png", "jpg", "jpeg"],
        key=_k("shot"),
    )

    if st.button("გარიგების შენახვა (Save Trade)", type="primary", key=_k("save")):
      # --- შემოწმება შენახვამდე: არასწორი მონაცემი ბაზაში არ ჩაიწერება ---
      errors = []
      if pd.isna(parsed_date):
        errors.append("თარიღი ვერ იკითხება")
      if to_float(entry_price) <= 0:
        errors.append("შეიყვანე შესვლის ფასი")
      rr_state = calculate_rr(side, entry_price, sl_price, tp_price)["status"]
      if rr_state == "bad_sl":
        errors.append("სტოპი არასწორ მხარესაა")
      if rr_state == "bad_tp":
        errors.append("ტეიკ პროფიტი არასწორ მხარესაა")
      if errors:
        st.error("არ შეინახა: " + "; ".join(errors) + ".")
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
          st.error(f"სკრინშოტის ატვირთვის შეცდომა: {upload_err}")

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
        st.toast("ახალი გარიგება წარმატებით შეიქმნა!", icon="✅")
        st.session_state["modal_gen"] = st.session_state.get("modal_gen", 0) + 1
        st.rerun()  # სრული rerun: ბარათების სია განახლდეს, ფორმა სუფთად დაიწყოს
      else:
        st.error("შენახვა ვერ მოხერხდა.")
