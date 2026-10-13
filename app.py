from database import fetch_trades, insert_trade
import streamlit as st
from utils.translations import t
from views.journal import render_journal_view
from views.settings import render_settings_view

st.set_page_config(
    page_title="Traders Lab - სავაჭრო ჟურნალი", page_icon="📊", layout="wide"
)

if "lang" not in st.session_state:
  st.session_state.lang = "ka"

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

# მთავარი მენიუ (დაემატა სეტინგების გვერდი)
st.sidebar.title(t("nav_header", lang))
menu = st.sidebar.selectbox(
    "აირჩიეთ გვერდი",
    ["📊 სავაჭრო ჟურნალი", "⚙️ სეტინგები და ცნობარები", "📈 ანალიტიკა"],
)

if menu == "📊 სავაჭრო ჟურნალი":
  render_journal_view(lang)

elif menu == "⚙️ სეტინგები და ცნობარები":
  render_settings_view(lang)

elif menu == "📈 ანალიტიკა":
  st.title("📈 სტატისტიკა და ანალიტიკა")
  df = fetch_trades()
  if not df.empty:
    st.metric(label="სულ გარიგებები", value=len(df))
  else:
    st.info("მონაცემები არ არის.")
