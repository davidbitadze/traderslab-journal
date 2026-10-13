from datetime import datetime
from database import fetch_settings, fetch_trades, insert_trade
import streamlit as st


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  df = fetch_trades()

  # ბაზიდან მოგვაქვს სეტინგებში გაწერილი პატერნები და ტრიგერები
  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")

  with st.popover("➕ ახალი გარიგების / მოქმედების დამატება"):
    st.subheader("ახალი ტრეიდის ან ნაწილობრივი მოქმედების ფორმა")

    with st.form("popover_trade_form"):
      col1, col2 = st.columns(2)

      with col1:
        entry_date = st.date_input("თარიღი (Entry Date)", datetime.today())
        pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
        side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
        entry_price = st.number_input(
            "შესვლის ფასი (Entry Price)", value=1.0850, format="%.5f"
        )
        qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0)
        formation = st.selectbox(
            "ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"]
        )

      with col2:
        action_type = st.selectbox(
            "მოქმედების ტიპი (ActionType)",
            [
                "Start Row in Journal (მთავარი შესვლა)",
                "Scale In (დამატება)",
                "Partial Exit (ნაწილობრივი დახურვა)",
                "Full Exit (სრული დახურვა)",
            ],
        )
        sl_price = st.number_input(
            "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f"
        )
        tp_price = st.number_input(
            "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f"
        )

        # სუფთა ჩამოსაშლელი მენიუები სეტინგებიდან
        pattern = st.selectbox("პატერნი (Pattern)", patterns_options)
        trigger = st.selectbox("ტრიგერი (Trigger)", triggers_options)

      description = st.text_area("აღწერა / კომენტარი (Description)", "")
      screenshot = st.file_uploader(
          "გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"]
      )

      submitted = st.form_submit_button("ბაზაში შენახვა (Save Trade)")

      if submitted:
        screenshot_name = screenshot.name if screenshot else "No Screenshot"

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
            "Formation": formation,
            "Description": description,
            "Screenshot": screenshot_name,
        }

        if insert_trade(trade_data):
          st.success("გარიგება წარმატებით შეინახა ბაზაში!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")

  st.divider()

  if not df.empty:
    st.write("📋 **არსებული ისტორია:**")
    st.data_editor(
        df,
        use_container_width=True,
        key="trade_journal_editor",
        num_rows="dynamic",
    )
  else:
    st.info("ცხრილი ამჟამად ცარიელია.")
