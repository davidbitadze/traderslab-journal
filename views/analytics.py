from database import fetch_trades
import pandas as pd
import streamlit as st


def render_analytics_view(lang="ka"):
  st.title("📈 სტატისტიკა და ანალიტიკა (Analytics)")
  st.divider()

  df = fetch_trades()

  if df.empty:
    st.info("ანალიტიკისთვის მონაცემები ჯერ არ არის ჟურნალში.")
    return

  st.subheader("🔍 ბაზის მონაცემების დიაგნოსტიკა:")
  st.write("სვეტები:", df.columns.tolist())

  # ვნახოთ ცხრილი სრულად, რომ ზუსტად ვნახოთ სად ინახება პატერნი და ტრიგერი
  st.dataframe(df, use_container_width=True)
