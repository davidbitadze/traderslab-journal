from database import fetch_trades, insert_trade
import streamlit as st
from views.add_trade import render_add_trade_view
from utils.translations import t

# 1. საიტის ძირითადი კონფიგურაცია აუცილებლად პირველი უნდა იყოს!
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
  # აქ გამოძახებულია ჩვენი ახალი მოდულური ფორმა, რომელიც ითვალისწინებს მრავალნაწილიან გარიგებებს
  render_add_trade_view(lang)

elif menu == t("menu_analytics", lang):
  st.title(t("analytics_title", lang))
  df = fetch_trades()
  if not df.empty:
    st.metric(label=t("total_trades", lang), value=len(df))
  else:
    st.info(t("empty_table", lang))
