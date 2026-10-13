from database import fetch_trades, insert_trade
import streamlit as st
from utils.translations import t
from views.journal import render_journal_view

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

# მთავარი მენიუ
st.sidebar.title(t("nav_header", lang))
menu = st.sidebar.selectbox(
    "აირჩიეთ გვერდი",
    [
        t("menu_journal", lang),
        t("menu_analytics", lang),
    ],
)

# გვერდების მიხედვით ჩვენება
if menu == t("menu_journal", lang):
  # აქ გამოიძახება ჟურნალისა და პოპაპ ფორმის ერთიანი სივრცე
  render_journal_view(lang)

elif menu == t("menu_analytics", lang):
  st.title(t("analytics_title", lang))
  df = fetch_trades()
  if not df.empty:
    st.metric(label=t("total_trades", lang), value=len(df))
  else:
    st.info(t("empty_table", lang))
