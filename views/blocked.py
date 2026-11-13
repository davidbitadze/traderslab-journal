import streamlit as st

from utils import auth
from utils.translations import t


def render_blocked_screen(user_email, account, lang):
  """გამოწერა ვადაგასულია/გამორთულია (ან ანგარიშის მონაცემები ვერ ჩაიტვირთა)."""
  st.sidebar.title(t("settings_title", lang))
  st.sidebar.write(f"👤 {user_email}")
  if st.sidebar.button(t("logout", lang), use_container_width=True):
    auth.logout()

  if account.load_failed:
    st.error(t("account_load_error", lang))
    if st.button(t("retry", lang)):
      st.session_state.pop("user_prefs", None)
      st.rerun()
  else:
    st.error(t("sub_expired_error", lang))
