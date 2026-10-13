import uuid
from datetime import datetime
from database import fetch_settings, fetch_trades, insert_trade, update_trade
import streamlit as st


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  df = fetch_trades()

  patterns_options = fetch_settings("pattern")
  triggers_options = fetch_settings("trigger")

  # ახალი გარიგების / მოქმედების დამატების პოპაპი
  with st.popover("➕ ახალი გარიგების / მოქმედების დამატება"):
    st.subheader("ტრეიდის გახსნა ან ნაწილობრივი მოქმედება (Action)")

    with st.form("popover_trade_form"):
      action_type = st.selectbox(
          "მოქმედების ტიპი (ActionType)",
          [
              "Start Row in Journal (მთავარი შესვლა)",
              "Scale In (დამატება პოზიციაში)",
              "Partial Exit (ნაწილობრივი დახურვა)",
              "Full Exit (სრული დახურვა)",
          ],
      )

      parent_trade_id = None
      if action_type != "Start Row in Journal (მთავარი შესვლა)":
        if not df.empty and "Trade ID" in df.columns:
          trade_choices = df["Trade ID"].dropna().unique().tolist()
          if trade_choices:
            selected_parent = st.selectbox(
                "აირჩიეთ დედა გარიგება (Parent Trade ID)",
                options=trade_choices,
                format_func=lambda x: f"Trade ID: {x}",
            )
            parent_trade_id = selected_parent

      st.divider()

      col1, col2 = st.columns(2)

      with col1:
        entry_date = st.date_input("თარიღი (Entry Date)", datetime.today())
        pair = st.text_input("ვალუტის წყვილი (Pair)", "EURUSD")
        side = st.selectbox("მიმართულება (Side)", ["Long", "Short"])
        entry_price = st.number_input(
            "ფასი (Price)", value=1.0850, format="%.5f"
        )
        qty = st.number_input("მოცულობა (Qty)", value=6000.0, step=100.0)

      with col2:
        formation = st.selectbox(
            "ფორმაცია (Formation)", ["ტრენდი", "კონტრ-ტრენდი", "ფლეტი"]
        )
        sl_price = st.number_input(
            "სტოპ ლოსი (SL Price)", value=1.0800, format="%.5f"
        )
        tp_price = st.number_input(
            "ტეიკ პროფიტი (TP Price)", value=1.0950, format="%.5f"
        )
        pattern = (
            st.selectbox("პატერნი (Pattern)", patterns_options)
            if patterns_options
            else ""
        )
        trigger = (
            st.selectbox("ტრიგერი (Trigger)", triggers_options)
            if triggers_options
            else ""
        )

      description = st.text_area("აღწერა / კომენტარი (Description)", "")
      screenshot = st.file_uploader(
          "გარიგების სკრინშოტი (Screenshot)", type=["png", "jpg", "jpeg"]
      )

      submitted = st.form_submit_button("მოქმედების შენახვა (Save Action)")

      if submitted:
        current_trade_id = str(uuid.uuid4())

        if action_type == "Start Row in Journal (მთავარი შესვლა)":
          final_parent_id = current_trade_id
        else:
          final_parent_id = (
              parent_trade_id if parent_trade_id else current_trade_id
          )

        screenshot_name = screenshot.name if screenshot else "No Screenshot"

        trade_data = {
            "Trade ID": current_trade_id,
            "Parent Trade ID": final_parent_id,
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
          st.success("მოქმედება/გარიგება წარმატებით დაემატა ბაზაში!")
          st.rerun()
        else:
          st.error("შენახვა ვერ მოხერხდა.")

  st.divider()

  # 📋 ცხრილი და ედიტირება
  if not df.empty:
    st.write(
        "📋 **სავაჭრო ისტორია და აქტიური პოზიციები:** (უჯრებში შეცვლილი"
        " მონაცემების შესანახად დააჭირეთ ქვედა ღილაკს)"
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        key="trade_journal_editor",
        num_rows="dynamic",
    )

    # ვამოწმებთ, მოხდა თუ არა რაიმე ცვლილება ედიტორში
    editor_state = st.session_state.get("trade_journal_editor", {})
    edited_rows = editor_state.get("edited_rows", {})

    if edited_rows:
      if st.button("💾 ცვლილებების შენახვა ბაზაში (Save Changes)"):
        success_count = 0
        for row_idx, updated_cols in edited_rows.items():
          # ვიღებთ კონკრეტული სტრიქონის Trade ID-ს
          trade_id = df.iloc[row_idx]["Trade ID"]
          if update_trade(trade_id, updated_cols):
            success_count += 1

        if success_count > 0:
          st.success(f"წარმატებით განახლდა {success_count} ჩანაწერი!")
          st.rerun()
        else:
          st.error("ცვლილებების შენახვა ვერ მოხერხდა.")
  else:
    st.info("ცხრილი ამჟამად ცარიელია.")
