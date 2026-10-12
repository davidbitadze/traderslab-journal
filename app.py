import pandas as pd
import streamlit as st
from supabase import create_client

# Supabase კავშირის ზუსტი მონაცემები
SUPABASE_URL = "https://sulifmgcdblvufmygjpg.supabase.co"
SUPABASE_KEY = (
    "sb_publishable_74vvbyKYiZ-8fFXdGfd0zQ_Ezk57..."  # თქვენი სრული კლავიში
)

st.title("📊 Traders Lab - სავაჭრო ჟურნალი")
st.write("ვებ-პლატფორმაზე გადატანილი სავაჭრო დღიური წარმატებით მუშაობს.")

try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

  # ახალი გარიგების დამატების ფორმა
  st.subheader("➕ ახალი გარიგების დამატება")
  with st.form("trade_form"):
    col1, col2 = st.columns(2)
    with col1:
      pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
      entry_price = st.text_input("შესვლის ფასი (Entry Price)", "1.0850")
      qty = st.text_input("მოცულობა (Qty)", "6000")
    with col2:
      side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
      pattern = st.text_input("პატერნი", "ვ-შემობრუნება")
      trigger = st.text_input("ტრიგერი", "ჩამოთვლა / მიწოლა")

    submit_button = st.form_submit_button(label="გარიგების შენახვა ბაზაში")

    if submit_button:
      # მონაცემების გაგზავნა Supabase-ში
      insert_data = {
          "Pair": pair,
          "Entry Price": entry_price,
          "Qty": qty,
          "Side": side,
          "Pattern": pattern,
          "Trigger": trigger,
      }
      res = supabase.table("trades").insert(insert_data).execute()
      st.success(
          f"გარიგება წარმატებით შეინახა ბაზაში! წყვილი: {pair}, მიმართულება:"
          f" {side}"
      )
      st.rerun()  # გვერდის განახლება, რომ ცხრილშიც გამოჩნდეს

  # არსებული გარიგებების წამოღება და ჩვენება
  response = supabase.table("trades").select("*").execute()
  data = response.data

  if data:
    df = pd.DataFrame(data)
    st.subheader("📋 არსებული გარიგებების ისტორია")
    st.dataframe(df)
  else:
    st.info("ცხრილი ამჟამად ცარიელია.")

except Exception as e:
  st.error(f"შეცდომა: {e}")
