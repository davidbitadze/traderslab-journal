import streamlit as st
from database import fetch_trades
from views import analytics  # თუ უკვე გაქვთ ფაილები views-ში

st.set_page_config(
    page_title="Traders Lab - სავაჭრო ჟურნალი", page_icon="📊", layout="wide"
)

st.sidebar.title("🧭 ნავიგაცია")
menu = st.sidebar.selectbox(
    "აირჩიეთ გვერდი", ["📊 სავაჭრო ჟურნალი", "➕ ახალი გარიგება", "📈 ანალიტიკა"]
)

if menu == "📊 სავაჭრო ჟურნალი":
  st.title("📊 არსებული გარიგებების ისტორია")
  df = fetch_trades()
  if not df.empty:
    st.dataframe(df, use_container_width=True)
  else:
    st.info("ცხრილი ამჟამად ცარიელია.")

elif menu == "➕ ახალი გარიგება":
  st.title("➕ ახალი გარიგების დამატება")
  from database import insert_trade

  with st.form("new_trade_form"):
    col1, col2 = st.columns(2)
    with col1:
      pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
      entry_price = st.text_input("შესვლის ფასი (Entry Price)", "1.0850")
      qty = st.text_input("მოცულობა (Qty)", "6000")
    with col2:
      side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
      pattern = st.text_input("პატერნი", "ვ-შემობრუნება")
      trigger = st.text_input("ტრიგერი", "ჩამოთვლა / მიწოლა")

    submitted = st.form_submit_button("გარიგების შენახვა ბაზაში")
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
        st.success("გარიგება წარმატებით შეინახა ბაზაში!")

elif menu == "📈 ანალიტიკა":
  st.title("📈 სტატისტიკა და ანალიტიკა")
  df = fetch_trades()
  if not df.empty:
    st.write(
        "სტატისტიკური პანელი მუშავდება... (აქ გადმოიტანება თქვენი Google"
        " Sheets-ის მე-3 გვერდის ლოგიკა)"
    )
    st.metric(
        label="სულ გარიგებები", value=len(df)
    )  # დროებითი ტესტ მეთრიკა
  else:
    st.info("მონაცემები არ არის ანალიტიკისთვის.")
