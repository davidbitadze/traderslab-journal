import html
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



_ROW_CSS = """
<style>
/* ცნობარის სტრიქონები (წაშლა · რედაქტირება · სახელი) მობილურზეც ერთ ხაზზე რჩება */
@media (max-width: 640px) {
  [data-testid="stHorizontalBlock"]:has(.setting-row-marker) {
    flex-wrap: nowrap !important;
    gap: 0.4rem !important;
    align-items: center !important;
  }
  [data-testid="stHorizontalBlock"]:has(.setting-row-marker) > div {
    width: auto !important;
    min-width: 0 !important;
    flex: 0 0 auto !important;
  }
  [data-testid="stHorizontalBlock"]:has(.setting-row-marker) > div:last-child {
    flex: 1 1 0 !important;
    overflow-wrap: anywhere;
  }
}
</style>
"""


def _item_label(text):
  """სახელი + უჩინარი მარკერი, რომლითაც CSS ამ სტრიქონებს ცნობს."""
  st.markdown(
      f"<span class='setting-row-marker'></span>{html.escape(str(text))}",
      unsafe_allow_html=True,
  )

def render_settings_view(lang="ka"):
  st.markdown(_ROW_CSS, unsafe_allow_html=True)
  st.title(f"⚙️ {t('settings_main_title', lang)}")
  st.write(t('settings_subtitle', lang))

  # --- ინტერფეისის მასშტაბისა და ვიზუალური ზომების მართვა ---
  st.markdown(f"### 📱 {t('screen_vis_title', lang)}")

  user_id = st.session_state.user.id if st.session_state.user else None
  user_prefs = st.session_state.get(
      "user_prefs",
      {"mobile_view_mode": "small", "desktop_view_mode": "medium"},
  )

  # დინამიური მასშტაბის ლეიბლები ენის მიხედვით
  scale_options = {
      t("scale_small", lang): "small",
      t("scale_medium", lang): "medium",
      t("scale_large", lang): "large",
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
        st.toast(t("visual_prefs_saved", lang), icon="✅")
        st.rerun()
      else:
        st.error(t("visual_prefs_error", lang))

  st.divider()

  # --- ბალანსის ტრანზაქციების (შევსება / გამოტანა) მართვა ---
  st.markdown(f"### 💰 {t('deposit_history_title', lang)}")

  with st.form("form_add_transaction"):
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
      txn_date = st.text_input(
          t("date_time_label", lang), value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      )
    with col_t2:
      txn_amount = st.number_input(
          t("amount_label", lang), value=500.0, step=50.0
      )
    with col_t3:
      txn_desc = st.text_input(t("note_label", lang))

    if st.form_submit_button(t("add_txn_btn", lang), use_container_width=True):
      import uuid

      new_txn = {
          "Transaction ID": str(uuid.uuid4()),
          "Date": txn_date,
          "Amount": str(txn_amount),
          "Description": txn_desc,
      }
      if add_balance_transaction(new_txn):
        st.success(t("txn_added_success", lang))
        st.rerun()

  # ტრანზაქციების სიის ჩვენება
  df_txn = fetch_balance_transactions()
  if not df_txn.empty:
    st.markdown(f"**{t('txn_journal_title', lang)}**")
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
            st.toast(t("txn_deleted_toast", lang), icon="🗑️")
            st.rerun()
  else:
    st.info(t("no_txn_msg", lang))

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
            st.success(f"{t('item_deleted', lang)}: {p}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          st.caption(f"{t('edit_pattern_caption', lang)}: {p}")
          updated_pat_name = st.text_input(
              t("new_name_label", lang), value=p, key=f"inp_pat_{p}"
          )
          if st.button(t("save_label", lang), key=f"btn_pat_{p}"):
            if updated_pat_name and updated_pat_name != p:
              if update_setting_item("pattern", p, updated_pat_name):
                st.success(t("update_success", lang))
                st.rerun()

      with c_txt:
        _item_label(p)

    st.divider()
    new_pat = st.text_input(t("new_pattern_placeholder", lang))
    if st.button(t("add_pattern_btn", lang)):
      if new_pat:
        if add_setting_item("pattern", new_pat):
          st.success(t("pattern_added_msg", lang, name=new_pat))
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
            st.success(f"{t('item_deleted', lang)}: {tr}")
            st.rerun()

      with c_edit:
        with st.popover("✏️"):
          st.caption(f"{t('edit_trigger_caption', lang)}: {tr}")
          updated_trig_name = st.text_input(
              t("new_name_label", lang), value=tr, key=f"inp_trig_{tr}"
          )
          if st.button(t("save_label", lang), key=f"btn_trig_{tr}"):
            if updated_trig_name and updated_trig_name != tr:
              if update_setting_item("trigger", tr, updated_trig_name):
                st.success(t("update_success", lang))
                st.rerun()

      with c_txt:
        _item_label(tr)

    st.divider()
    new_trig = st.text_input(t("new_trigger_placeholder", lang))
    if st.button(t("add_trigger_btn", lang)):
      if new_trig:
        if add_setting_item("trigger", new_trig):
          st.success(t("trigger_added_msg", lang, name=new_trig))
          st.rerun()
