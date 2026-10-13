from database import (
    add_setting_item,
    delete_setting_item,
    fetch_settings,
)
import streamlit as st


def render_settings_view(lang="ka"):
  st.title("⚙️ პლატფორმის სეტინგები და ცნობარები (Settings & Master Data)")
  st.write(
      "აქ შეგიძლიათ დაამატოთ ან წაშალოთ პატერნები და ტრიგერები, რომლებიც"
      " ავტომატურად აისახება სავაჭრო ჟურნალის ფორმაში."
  )

  col1, col2 = st.columns(2)

  # --- პატერნების მართვა ---
  with col1:
    st.subheader("📌 პატერნების მართვა (Patterns)")
    patterns = fetch_settings("pattern")

    # არსებულების ჩვენება და წაშლის შესაძლებლობა
    for p in patterns:
      c_del, c_txt = st.columns([1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_pat_{p}"):
          if delete_setting_item("pattern", p):
            st.success(f"წაიშალა: {p}")
            st.rerun()
      with c_txt:
        st.write(p)

    st.divider()
    new_pat = st.text_input("ახალი პატერნის სახელი")
    if st.button("პატერნის დამატება"):
      if new_pat:
        if add_setting_item("pattern", new_pat):
          st.success(f"პატერნი '{new_pat}' დაემატა!")
          st.rerun()
        else:
          st.error("ვერ მოხერხდა დამატება.")

  # --- ტრიგერების მართვა ---
  with col2:
    st.subheader("⚡ ტრიგერების მართვა (Triggers)")
    triggers = fetch_settings("trigger")

    for tr in triggers:
      c_del, c_txt = st.columns([1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_trig_{tr}"):
          if delete_setting_item("trigger", tr):
            st.success(f"წაიშალა: {tr}")
            st.rerun()
      with c_txt:
        st.write(tr)

    st.divider()
    new_trig = st.text_input("ახალი ტრიგერის სახელი")
    if st.button("ტრიგერის დამატება"):
      if new_trig:
        if add_setting_item("trigger", new_trig):
          st.success(f"ტრიგერი '{new_trig}' დაემატა!")
          st.rerun()
        else:
          st.error("ვერ მოხერხდა დამატება.")
