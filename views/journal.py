from datetime import datetime
from database import fetch_trades, insert_trade
import streamlit as st


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  # სესიის ინიციალიზაცია პატერნებისა და ტრიგერებისთვის, რომ იუზერმა შეძლოს მათი დინამიკურად გაფართოება
  if "patterns_list" not in st.session_state:
    st.session_state.patterns_list = [
        "ვ-შემობრუნება",
        "ორმაგი წვერი",
        "თავი მხრები",
    ]

  if "triggers_list" not in st.session_state:
    st.session_state.triggers_list = ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]

  # მონაცემების წამოღება ბაზიდან
  df = fetch_trades()

  # პოპაპ ფანჯარა ახალი გარიგების დასამატებლად
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

        # ფორმაცია (ტრენდი, კონტრ-ტრენდი, ფლეტი)
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

        # დინამიკური პატერნების არჩევანი
        selected_pattern = st.selectbox(
            "პატერნი (Pattern)", st.session_state.patterns_list
        )

        # დინამიკური ტრიგერების არჩევანი
        selected_trigger = st.selectbox(
            "ტრიგერი (Trigger)", st.session_state.triggers_list
        )

      # ტექსტური ველები ახალი პატერნის ან ტრიგერის დასამატებლად სურვილისამებრ
      st.divider()
      st.write("🔧 **საკუთარი კომბინაციების დამატება:**")
      col_add1, col_add2 = st.columns(2)
      with col_add1:
        custom_pattern = st.text_input(
            "ახალი პატერნის დამატება (თუ სიაში არ არის)"
        )
      with col_add2:
        custom_trigger = st.text_input(
            "ახალი ტრიგერის დამატება (თუ სიაში არ არის)"
        )

      description = st.text_area("აღწერა / კომენტარი (Description)", "")
      screenshot = st.file_uploader(
          "გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"]
      )

      submitted = st.form_submit_button("ბაზაში შენახვა (Save Trade)")

      if submitted:
        # თუ იუზერმა შემოიყვანა ახალი პატერნი ან ტრიგერი, ვამატებთ სიებში
        final_pattern = custom_pattern if custom_pattern else selected_pattern
        if custom_pattern and custom_pattern not in st.session_state.patterns_list:
          st.session_state.patterns_list.append(custom_pattern)

        final_trigger = custom_trigger if custom_trigger else selected_trigger
        if custom_trigger and custom_trigger not in st.session_state.triggers_list:
          st.session_state.triggers_list.append(custom_trigger)

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
            "Pattern": final_pattern,
            "Trigger": final_trigger,
            "Formation": formation,
            "Description": description,
            "Screenshot": screenshot_name,
        }

        if insert_trade(trade_data):
          st.success("გარიგება და დეტალები წარმატებით შეინახა ბაზაში!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")

  st.divider()

  # ცხრილი
  if not df.empty:
    st.write(
        "📋 **არსებული ისტორია** (შეგიძლიათ პირდაპირ უჯრებში შეიტანოთ ცვლილებები):"
    )
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        key="trade_journal_editor",
        num_rows="dynamic",
    )
  else:
    st.info(
        "ცხრილი ამჟამად ცარიელია. გამოიყენეთ ზედა ღილაკი პირველი გარიგების"
        " ჩასაწერად."
    )
