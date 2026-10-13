from database import fetch_trades, update_trade
import streamlit as st
from views.add_trade_modal import render_add_trade_modal


def render_journal_view(lang="ka"):
  st.title(
      "📊 სავაჭრო ჟურნალი და მრავალნაწილიანი გარიგებების მართვა (Trading"
      " Journal)"
  )

  df = fetch_trades()

  # მოდალური ფორმის გამოძახება
  render_add_trade_modal(df)

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
    st.info("ცხრილი ამჟამად ცარიელია.")
