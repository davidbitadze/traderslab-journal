from database import fetch_trades
import streamlit as st


def render_analytics_view(lang="ka"):
  st.title("📈 სტატისტიკა და ანალიტიკა (Analytics)")
  st.divider()

  df = fetch_trades()

  if df.empty:
    st.info("ბაზა ცარიელია.")
    return

  st.subheader("ბაზიდან წამოღებული სრული მონაცემები:")
  st.dataframe(df, use_container_width=True)

  # ვნახოთ სვეტები
  st.write("სვეტები:", df.columns.tolist())
