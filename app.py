from database import fetch_trades, insert_trade
import streamlit as st
from utils.translations import t

st.set_page_config(
    page_title="Traders Lab - სავაჭრო ჟურნალი", page_icon="📊", layout="wide"
)

# ენის მართვის სესიის ინიციალიზაცია
if "lang" not in st.session_state:
  st.session_state.lang = "ka"

# Sidebar - ენის არჩევანი და ნავიგაცია
st.sidebar.title("⚙️ Settings / პარამეტრები")
selected_lang = st.sidebar.selectbox(
    "Language / ენა",
    options=["ka", "en"],
    format_func=lambda x: "🇬🇪 ქართული" if x == "ka" else "🇬🇧 English",
    index=0 if st.session_state.lang == "ka" else 1,
)

if selected_lang != st.session_state.lang:
  st.session_state.lang = selected_lang
  st.rerun()

lang = st.session_state.lang

# მენიუ
st.sidebar.title(t("nav_header", lang))
menu = st.sidebar.selectbox(
    "აირჩიეთ გვერდი",
    [
        t("menu_journal", lang),
        t("menu_add", lang),
        t("menu_analytics", lang),
    ],
)

# გვერდების ლოგიკა
if menu == t("menu_journal", lang):
  st.title(t("journal_title", lang))
  df = fetch_trades()
  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info(t("empty_table", lang))

elif menu == t("menu_add", lang):
  st.title(t("add_title", lang))
  with st.form("new_trade_form"):
    col1, col2 = st.columns(2)
    with col1:
      pair = st.text_input(t("pair", lang), "EURUSD")
      entry_price = st.text_input(t("entry_price", lang), "1.0850")
      qty = st.text_input(t("qty", lang), "6000")
    with col2:
      side = st.selectbox(t("side", lang), ["Long", "Short"])
      pattern = st.text_input(t("pattern", lang), "ვ-შემობრუნება")
      trigger = st.text_input(t("trigger", lang), "ჩამოთვლა / მიწოლა")

    submitted = st.form_submit_button(t("save_btn", lang))
    if submitted:
      data = {
          "Pair": pair,
          "Entry Price": entry_price,
          "Qty": qty,
          "Side": side,
          "Pattern": pattern,
          "Trigger": trigger,
      }
      if insert_trade(data):
        st.success(t("success_save", lang))

elif menu == t("menu_analytics", lang):
  st.title(t("analytics_title", lang))
  df = fetch_trades()
  if not df.empty:
    st.metric(label=t("total_trades", lang), value=len(df))
  else:
    st.info(t("empty_table", lang))
