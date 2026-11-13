from datetime import datetime
from database import (
    add_balance_transaction,
    add_setting_item,
    delete_balance_transaction,
    delete_setting_item,
    fetch_balance_transactions,
    fetch_settings,
    update_setting_item,
    upsert_user_preferences,
)
import streamlit as st
from utils.translations import t


def render_settings_view(lang="ka"):
  st.title(f"⚙️ {t('settings_main_title', lang)}")
  st.write(t('settings_subtitle', lang))

  # --- ინტერფეისის მასშტაბისა და ვიზუალური ზომების მართვა ---
  st.markdown(f"### 📱 {t('screen_vis_title', lang)}")

  user_id = st.session_state.user.id if st.session_state.user else None
  user_prefs = st.session_state.get(
      "user_prefs",
      {"mobile_view_mode": "small", "desktop_view_mode": "medium"},
  )

  scale_options = {
      t("scale_small", lang) if "scale_small" in t(lang) else "პატარა (კომპაქტური)": "small",
      t("scale_medium", lang) if "scale_medium" in t(lang) else "საშუალო (სტანდარტული)": "medium",
      t("scale_large", lang) if "scale_large" in t(lang) else "დიდი (გაფართოებული)": "large",
  }
  options_keys = list(scale_options.keys())
  options_vals = list(scale_options.values())

  col_m, col_d = st.columns(2)

  with col_m:
    curr_mob = user_prefs.get("mobile_view_mode", "small")
    mob_idx = options_vals.index(curr_mob) if curr_mob in options_vals else 0
    selected_mob = st.selectbox(
        t('mobile_view_label', lang),
        options=options_keys,
        index=mob_idx,
        key="sb_mobile_scale",
    )

  with col_d:
    curr_desk = user_prefs.get("desktop_view_mode", "medium")
    desk_idx = options_vals.index(curr_desk) if curr_desk in options_vals else 1
    selected_desk = st.selectbox(
        t('desktop_view_label', lang),
        options=options_keys,
        index=desk_idx,
        key="sb_desktop_scale",
    )

  new_mob_val = scale_options[selected_mob]
  new_desk_val = scale_options[selected_desk]

  if new_mob_val != curr_mob or new_desk_val != curr_desk:
    if user_id:
      if upsert_user_preferences(
          user_id, mobile_mode=new_mob_val, desktop_mode=new_desk_val
      ):
        st.session_state.user_prefs["mobile_view_mode"] = new_mob_val
        st.session_state.user_prefs["desktop_view_mode"] = new_desk_val
        success_msg = t("visual_prefs_saved", lang) if "visual_prefs_saved" in t(lang) else "ვიზუალური პარამეტრები შენახულია ბაზაში!"
        st.toast(success_msg, icon="✅")
        st.rerun()
      else:
        err_msg = t("visual_prefs_error", lang) if "visual_prefs_error" in t(lang) else "პარამეტრების ბაზაში შენახვა ვერ მოხერხდა."
        st.error(err_msg)

  st.divider()

  # --- ბალანსის ტრანზაქციების (შევსება / გამოტანა) მართვა ---
  st.markdown(f"### 💰 {t('deposit_history_title', lang)}")

  date_label = t("date_time_label", lang) if "date_time_label" in t(lang) else "თარიღი და დრო"
  amount_label = t("amount_label", lang) if "amount_label" in t(lang) else "თანხა ($) (+ შევსება, - გამოტანა)"
  note_label = t("note_label", lang) if "note_label" in t(lang) else "შენიშვნა (მაგ. საწყისი დეპოზიტი)"
  add_txn_btn = t("add_txn_btn", lang) if "add_txn_btn" in t(lang) else "➕ ტრანზაქციის დამატება"

  with st.form("form_add_transaction"):
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
      txn_date = st.text_input(
          date_label, value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )
    with col_t2:
      txn_amount = st.number_input(
          amount_label, value=500.0, step=50.0
      )
    with col_t3:
      txn_desc = st.text_input(note_label)

    if st.form_submit_button(add_txn_btn, use_container_width=True):
      import uuid

      new_txn = {
          "Transaction ID": str(uuid.uuid4()),
          "Date": txn_date,
          "Amount": str(txn_amount),
          "Description": txn_desc,
      }
      if add_balance_transaction(new_txn):
        success_txn = t("txn_added_success", lang) if "txn_added_success" in t(lang) else "ტრანზაქცია წარმატებით დაემატა!"
        st.success(success_txn)
        st.rerun()

  # ტრანზაქციების სიის ჩვენება
  df_txn = fetch_balance_transactions()
  if not df_txn.empty:
    journal_title_txt = t("txn_journal_title", lang) if "txn_journal_title" in t(lang) else "📋 ტრანზაქციების ჟურნალი:"
    st.markdown(f"**{journal_title_txt}**")
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
            del_toast = t("txn_deleted_toast", lang) if "txn_deleted_toast" in t(lang) else "ტრანზაქცია წაიშალა!"
            st.toast(del_toast, icon="🗑️")
            st.rerun()
  else:
    no_txn_msg = t("no_txn_msg", lang) if "no_txn_msg" in t(lang) else "ბალანსის ტრანზაქციები ჯერ არ არის მითითებული."
    st.info(no_txn_msg)

  st.divider()

  col1, col2 = st.columns(2)

  # --- პატერნების მართვა ---
  with col1:
    st.subheader(f"📌 {t('patterns_title', lang)}")
    patterns = fetch_settings("pattern")

    for p in patterns:
      c_del, c_edit, c_txt = st.columns([1, 1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_pat_{p}"):
          if delete_setting_item("pattern", p):
            deleted_txt = t("item_deleted", lang) if "item_deleted" in t(lang) else "წაიშალა"
            st.success(f"{deleted_txt}: {p}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          edit_caption = t("edit_pattern_caption", lang, name=p) if "edit_pattern_caption" in t(lang) else f"პატერნის შეცვლა: {p}"
          st.caption(edit_caption)
          new_name_label = t("new_name_label", lang) if "new_name_label" in t(lang) else "ახალი სახელი"
          save_label = t("save_label", lang) if "save_label" in t(lang) else "შენახვა"
          
          updated_pat_name = st.text_input(
              new_name_label, value=p, key=f"inp_pat_{p}"
          )
          if st.button(save_label, key=f"btn_pat_{p}"):
            if updated_pat_name and updated_pat_name != p:
              if update_setting_item("pattern", p, updated_pat_name):
                updated_success = t("update_success", lang) if "update_success" in t(lang) else "წარმატებით განახლდა!"
                st.success(updated_success)
                st.rerun()

      with c_txt:
        st.write(p)

    st.divider()
    new_pat_placeholder = t("new_pattern_placeholder", lang) if "new_pattern_placeholder" in t(lang) else "ახალი პატერნის დამატება"
    add_pat_btn = t("add_pattern_btn", lang) if "add_pattern_btn" in t(lang) else "დამატება პატერნებში"
    
    new_pat = st.text_input(new_pat_placeholder)
    if st.button(add_pat_btn):
      if new_pat:
        if add_setting_item("pattern", new_pat):
          pat_added_msg = t("pattern_added_msg", lang, name=new_pat) if "pattern_added_msg" in t(lang) else f"პატერნი '{new_pat}' დაემატა!"
          st.success(pat_added_msg)
          st.rerun()

  # --- ტრიგერების მართვა ---
  with col2:
    st.subheader(f"⚡ {t('triggers_title', lang)}")
    triggers = fetch_settings("trigger")

    for tr in triggers:
      c_del, c_edit, c_txt = st.columns([1, 1, 4])
      with c_del:
        if st.button("🗑️", key=f"del_trig_{tr}"):
          if delete_setting_item("trigger", tr):
            deleted_txt = t("item_deleted", lang) if "item_deleted" in t(lang) else "წაიშალა"
            st.success(f"{deleted_txt}: {tr}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          edit_trig_caption = t("edit_trigger_caption", lang, name=tr) if "edit_trigger_caption" in t(lang) else f"ტრიგერის შეცვლა: {tr}"
          st.caption(edit_trig_caption)
          new_name_label = t("new_name_label", lang) if "new_name_label" in t(lang) else "ახალი სახელი"
          save_label = t("save_label", lang) if "save_label" in t(lang) else "შენახვა"

          updated_trig_name = st.text_input(
              new_name_label, value=tr, key=f"inp_trig_{tr}"
          )
          if st.button(save_label, key=f"btn_trig_{tr}"):
            if updated_trig_name and updated_trig_name != tr:
              if update_setting_item("trigger", tr, updated_trig_name):
                updated_success = t("update_success", lang) if "update_success" in t(lang) else "წარმატებით განახლდა!"
                st.success(updated_success)
                st.rerun()

      with c_txt:
        st.write(tr)

    st.divider()
    new_trig_placeholder = t("new_trigger_placeholder", lang) if "new_trigger_placeholder" in t(lang) else "ახალი ტრიგერის დამატება"
    add_trig_btn = t("add_trigger_btn", lang) if "add_trigger_btn" in t(lang) else "დამატება ტრიგერებში"

    new_trig = st.text_input(new_trig_placeholder)
    if st.button(add_trig_btn):
      if new_trig:
        if add_setting_item("trigger", new_trig):
          trig_added_msg = t("trigger_added_msg", lang, name=new_trig) if "trigger_added_msg" in t(lang) else f"ტრიგერი '{new_trig}' დაემატა!"
          st.success(trig_added_msg)
          st.rerun()
