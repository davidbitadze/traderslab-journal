from datetime import datetime
from database import (
    add_balance_transaction,
    add_setting_item,
    delete_balance_transaction,
    delete_setting_item,
    fetch_balance_transactions,
    fetch_settings,
    update_setting_item,
)
import streamlit as st


def render_settings_view(lang="ka"):
  st.title("⚙️ კონფიგურაცია და პარამეტრები (Settings)")
  st.write(
      "მართეთ პლატფორმის ძირითადი ცნობარები, სავაჭრო ელემენტები და ფინანსური"
      " ბალანსი."
  )

  # --- ბალანსის ტრანზაქციების (შევსება / გამოტანა) მართვა ---
  st.markdown("### 💰 დეპოზიტისა და ბალანსის ისტორია")

  with st.form("form_add_transaction"):
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
      txn_date = st.text_input(
          "თარიღი და დრო", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )
    with col_t2:
      txn_amount = st.number_input(
          "თანხა ($) (+ შევსება, - გამოტანა)", value=500.0, step=50.0
      )
    with col_t3:
      txn_desc = st.text_input("შენიშვნა (მაგ. საწყისი დეპოზიტი)")

    if st.form_submit_button("➕ ტრანზაქციის დამატება", use_container_width=True):
      import uuid

      new_txn = {
          "Transaction ID": str(uuid.uuid4()),
          "Date": txn_date,
          "Amount": str(txn_amount),
          "Description": txn_desc,
      }
      if add_balance_transaction(new_txn):
        st.success("ტრანზაქცია წარმატებით დაემატა!")
        st.rerun()

  # ტრანზაქციების სიის ჩვენება
  df_txn = fetch_balance_transactions()
  if not df_txn.empty:
    st.markdown("**📋 ტრანზაქციების ჟურნალი:**")
    for _, txn in df_txn.iterrows():
      t_id = txn.get("Transaction ID")
      col_r1, col_r2, col_r3, col_r4 = st.columns([2, 2, 4, 1])
      with col_r1:
        st.write(txn.get("Date"))
      with col_r2:
        amount_val = float(txn.get("Amount", 0))
        color = "green" if amount_val >= 0 else "red"
        st.markdown(
            f"<b style='color:{color};'>{amount_val:+.2f}$</b>",
            unsafe_allow_html=True,
        )
      with col_r3:
        st.write(txn.get("Description", ""))
      with col_r4:
        if st.button("🗑️", key=f"del_txn_{t_id}"):
          if delete_balance_transaction(t_id):
            st.toast("ტრანზაქცია წაიშალა!", icon="🗑️")
            st.rerun()
  else:
    st.info("ბალანსის ტრანზაქციები ჯერ არ არის მითითებული.")

  st.divider()

  col1, col2 = st.columns(2)

  # --- პატერნების მართვა ---
  with col1:
    st.subheader("📌 პატერნების სია (Patterns)")
    patterns = fetch_settings("pattern")

    for p in patterns:
      c_del, c_edit, c_txt = st.columns([1, 1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_pat_{p}"):
          if delete_setting_item("pattern", p):
            st.success(f"წაიშალა: {p}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          st.caption(f"პატერნის შეცვლა: {p}")
          updated_pat_name = st.text_input(
              "ახალი სახელი", value=p, key=f"inp_pat_{p}"
          )
          if st.button("შენახვა", key=f"btn_pat_{p}"):
            if updated_pat_name and updated_pat_name != p:
              if update_setting_item("pattern", p, updated_pat_name):
                st.success("წარმატებით განახლდა!")
                st.rerun()

      with c_txt:
        st.write(p)

    st.divider()
    new_pat = st.text_input("ახალი პატერნის დამატება")
    if st.button("დამატება პატერნებში"):
      if new_pat:
        if add_setting_item("pattern", new_pat):
          st.success(f"პატერნი '{new_pat}' დაემატა!")
          st.rerun()

  # --- ტრიგერების მართვა ---
  with col2:
    st.subheader("⚡ ტრიგერების სია (Triggers)")
    triggers = fetch_settings("trigger")

    for tr in triggers:
      c_del, c_edit, c_txt = st.columns([1, 1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_trig_{tr}"):
          if delete_setting_item("trigger", tr):
            st.success(f"წაიშალა: {tr}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          st.caption(f"ტრიგერის შეცვლა: {tr}")
          updated_trig_name = st.text_input(
              "ახალი სახელი", value=tr, key=f"inp_trig_{tr}"
          )
          if st.button("შენახვა", key=f"btn_trig_{tr}"):
            if updated_trig_name and updated_trig_name != tr:
              if update_setting_item("trigger", tr, updated_trig_name):
                st.success("წარმატებით განახლდა!")
                st.rerun()

      with c_txt:
        st.write(tr)

    st.divider()
    new_trig = st.text_input("ახალი ტრიგერის დამატება")
    if st.button("დამატება ტრიგერებში"):
      if new_trig:
        if add_setting_item("trigger", new_trig):
          st.success(f"ტრიგერი '{new_trig}' დაემატა!")
          st.rerun()
