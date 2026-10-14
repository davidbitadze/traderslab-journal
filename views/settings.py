from database import (
    add_setting_item,
    delete_setting_item,
    fetch_settings,
    update_setting_item,
)
import streamlit as st


def render_settings_view(lang="ka"):
  st.title("⚙️ კონფიგურაცია და პარამეტრები (Settings)")
  st.write(
      "მართეთ პლატფორმის ძირითადი ცნობარები, სავაჭრო ელემენტები და ფინანსური"
      " პარამეტრები."
  )

  # --- ახალი ფინანსური პარამეტრების სექცია (საწყისი დეპოზიტი) ---
  st.markdown("### 💰 საწყისი დეპოზიტის მართვა")
  current_deposit = st.session_state.get("initial_deposit", 500.0)

  col_dep1, col_dep2 = st.columns([2, 1])
  with col_dep1:
    initial_deposit = st.number_input(
        "საწყისი დეპოზიტი ($)",
        value=float(current_deposit),
        step=50.0,
        key="inp_initial_deposit",
    )
  with col_dep2:
    st.write("")  # გასწორებისთვის
    st.write("")
    if st.button("💾 დეპოზიტის შენახვა", use_container_width=True):
      st.session_state["initial_deposit"] = initial_deposit
      st.success("საწყისი დეპოზიტი წარმატებით განახლდა!")

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
