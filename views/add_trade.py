import streamlit as st
from database import insert_trade
from datetime import datetime
from utils.translations import t


def render_add_trade_view(lang="ka"):
  st.subheader(
      "➕ ახალი გარიგების / ნაწილობრივი მოქმედების დამატება (Trade Action)"
  )

  with st.form("detailed_trade_form"):
    col1, col2 = st.columns(2)

    with col1:
      entry_date = st.date_input("თარიღი (Entry Date)", datetime.today())
      pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
      side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
      entry_price = st.number_input(
          "შესვლის ფასი (Entry Price)", value=1.0850, format="%.5f"
      )
      qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0)
      sl_price = st.number_input(
          "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f"
      )
      tp_price = st.number_input(
          "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f"
      )

    with col2:
      action_type = st.selectbox(
          "მოქმედების ტიპი (ActionType)",
          [
              "Start Row in Journal (მთავარი შესვლა)",
              "Scale In (დამატება პოზიციაში)",
              "Partial Exit (ნაწილობრივი დახურვა)",
              "Full Exit (სრული დახურვა)",
          ],
      )
      pattern = st.text_input("პატერნი (Pattern)", "ვ-შემობრუნება")
      trigger = st.text_input("ტრიგერი (Trigger)", "ჩამოთვლა / მიწოლა")
      trend = st.selectbox("ტრენდი (Trend)", ["მიმდინარე", "კორექცია", "ფლეთი"])
      risk_reward = st.text_input(
          "რისკის და მოგების თანაფარდობა (R/R)", "1:2"
      )
      description = st.text_area("აღწერა / კომენტარი (Description)", "")

    submitted = st.form_submit_button(
        "გარიგების ჩაწერა ბაზაში (Submit Trade)"
    )

    if submitted:
      trade_data = {
          "Entry Date": str(entry_date),
          "Pair": pair,
          "Side": side,
          "Entry Price": str(entry_price),
          "Qty": str(qty),
          "SL_Price": str(sl_price),
          "TP_Price": str(tp_price),
          "ActionType": action_type,
          "Pattern": pattern,
          "Trigger": trigger,
          "Trend": trend,
          "Risk_Reward": risk_reward,
          "Description": description,
      }

      if insert_trade(trade_data):
        st.success(
            "გარიგების დეტალები წარმატებით შეინახა ბაზაში! (Trade Action"
            " Logged)"
        )
      else:
        st.error(
            "მონაცემთა შენახვა ვერ მოხერხდა. შეამოწმეთ ველები ან ბაზის კავშირი."
        )
