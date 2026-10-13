import uuid
from datetime import datetime
from database import fetch_settings, fetch_trades, insert_trade, update_trade
import streamlit as st
from views.add_trade_modal import render_add_trade_modal


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  df = fetch_trades()

  # 1. მხოლოდ ახალი მთავარი გარიგების ღილაკი
  render_add_trade_modal()

  st.divider()

  if not df.empty:
    # 2. არსებული გარიგების მართვა (Scale In / Exit) სექცია
    with st.expander(
        "⚙️ არსებული პოზიციის მართვა (დამატება / ნაწილობრივი ან სრული"
        " ჩახურვა)"
    ):
      st.write(
          "აირჩიეთ არსებული გარიგება და მიაბას მას ახალი ეტაპობრივი მოქმედება."
      )

      with st.form("sub_action_form"):
        parent_choices = df["Trade ID"].dropna().unique().tolist()
        selected_parent = st.selectbox(
            "აირჩიეთ დედა გარიგება (Parent Trade ID)",
            options=parent_choices,
            format_func=lambda x: f"ID: {x[:8]}... ({df[df['Trade ID']==x]['Pair'].values[0] if 'Pair' in df.columns else ''})",
        )

        action_type = st.selectbox(
            "მოქმედების ტიპი",
            [
                "Scale In (დამატება პოზიციაში)",
                "Partial Exit (ნაწილობრივი დახურვა)",
                "Full Exit (სრული დახურვა)",
            ],
        )

        col1, col2 = st.columns(2)
        with col1:
          sub_price = st.number_input(
              "მოქმედების ფასი (Price)", value=1.0850, format="%.5f"
          )
          sub_qty = st.number_input("მოცულობა (Qty)", value=3000.0, step=100.0)
        with col2:
          sub_date = st.date_input("თარიღი", datetime.today())
          sub_desc = st.text_input("კომენტარი მოქმედებაზე", "")

        sub_submitted = st.form_submit_button("მოქმედების მიბმა პოზიციაზე")

        if sub_submitted and selected_parent:
          # ვეძებთ მშობელი გარიგების წყვილს და მიმართულებას
          matched_row = df[df["Trade ID"] == selected_parent]
          pair_val = (
              matched_row.iloc[0]["Pair"]
              if not matched_row.empty and "Pair" in matched_row.columns
              else "EURUSD"
          )
          side_val = (
              matched_row.iloc[0]["Side"]
              if not matched_row.empty and "Side" in matched_row.columns
              else "Long"
          )

          child_trade_data = {
              "Trade ID": str(uuid.uuid4()),
              "Parent Trade ID": selected_parent,
              "Entry Date": str(sub_date),
              "Pair": pair_val,
              "Side": side_val,
              "Entry Price": str(sub_price),
              "Qty": str(sub_qty),
              "ActionType": action_type,
              "Description": sub_desc,
          }

          if insert_trade(child_trade_data):
            st.success("მოქმედება წარმატებით მიება პოზიციას!")
            st.rerun()
          else:
            st.error("მოქმედების დამატება ვერ მოხერხდა.")

    st.divider()

    # 3. ცხრილი და პირდაპირი ედიტირება
    st.write(
        "📋 **სავაჭრო ისტორია და აქტიური პოზიციები:** (უჯრებში ცვლილებების"
        " შესანახად გამოიყენეთ ქვედა ღილაკი)"
    )

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        key="trade_journal_editor",
        num_rows="dynamic",
    )

    editor_state = st.session_state.get("trade_journal_editor", {})
    edited_rows = editor_state.get("edited_rows", {})

    if edited_rows:
      if st.button("💾 ცვლილებების შენახვა ბაზაში (Save Changes)"):
        success_count = 0
        for row_idx, updated_cols in edited_rows.items():
          trade_id = df.iloc[row_idx]["Trade ID"]
          if update_trade(trade_id, updated_cols):
            success_count += 1

        if success_count > 0:
          st.success(f"წარმატებით განახლდა {success_count} ჩანაწერი!")
          st.rerun()
        else:
          st.error("ცვლილებების შენახვა ვერ მოხერხდა.")
  else:
    st.info("ცხრილი ამჟამად ცარიელია. დაამატეთ პირველი გარიგება.")
