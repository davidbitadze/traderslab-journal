import pandas as pd
import streamlit as st
from supabase import create_client

# 1. Supabase კავშირის ინიციალიზაცია (secrets-იდან ან პირდაპირი გასაღებებით)
SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL", "თქვენი_supabase_url_აქ"
)  # დროებით ან სქრეტებიდან
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "თქვენი_supabase_key_აქ")

# სათაური და ინტერფეისი
st.title("📊 Traders Lab - სავაჭრო ჟურნალი")
st.write(
    "მოგესალმებით! ეს არის თქვენი განახლებული, ვებ-პლატფორმაზე გადატანილი"
    " სავაჭრო დღიური."
)

# 2. მონაცემების წამოღება Supabase-იდან
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
  response = supabase.table("trades").select("*").execute()
  data = response.data

  if data:
    df = pd.DataFrame(data)
    st.subheader("📋 არსებული გარიგებების ისტორია")
    st.dataframe(df)
  else:
    st.info(
        "ცხრილი ცარიელია ან მონაცემები ჯერ არ ჩანს. სცადეთ მონაცემების დამატება."
    )

except Exception as e:
  st.error(
      "გთხოვთ მიუთითოთ Supabase კავშირის გასაღებები (URL და Key). შეცდომა:"
      f" {e}"
  )

# 3. მარტივი ფორმა ახალი გარიგების დასამატებლად (MVP)
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

  submit_button = st.form_submit_button(
      label="გარიგების შენახვა ბაზაში"
  )

  if submit_button:
    st.success(
        f"მონაცემები წარმატებით დამუშავდა! წყვილი: {pair}, მიმართულება: {side}"
    )
    # აქ მოხდება ბაზაში ჩაწერა შემდეგ ნაბიჯზე
