import streamlit as st

from i18n import detect_browser_lang, normalize_lang
from utils import auth
from utils.account import load_account
from utils.db_preferences import update_user_preference_fields
from utils.sidebar_manager import render_sidebar_and_navigation
from utils.theme import apply_ui_scaling, detect_is_mobile
from views.blocked import render_blocked_screen
from views.login import render_auth_screen

st.set_page_config(page_title="Traders Lab", page_icon="📊", layout="wide")

st.session_state.setdefault("lang", detect_browser_lang())
st.session_state.setdefault("user", None)

# ძველი URL-პარამეტრების გასუფთავება
for _old_key in ("saved_email", "saved_uid"):
  if _old_key in st.query_params:
    del st.query_params[_old_key]

auth.restore_session()
auth.ensure_fresh_session()
auth.flush_cookie_cmd()

if st.session_state.user is None:
  render_auth_screen()
else:
  user_id = st.session_state.user.id
  user_email = st.session_state.user.email
  account = load_account(user_id)

  # დიაგნოსტიკა (?debug=1) მხოლოდ ბაზაში დადასტურებულ ადმინს ეჩვენება
  if st.query_params.get("debug") == "1" and account.is_admin:
    auth.render_debug()

  # ენა/თემა ბაზიდან
  prefs = account.prefs
  saved_lang = prefs.get("language")
  st.session_state.lang = normalize_lang(saved_lang or st.session_state.get("lang"))
  if not saved_lang:
    # ახალი მომხმარებელი: ბრაუზერის (ან შესვლის გვერდზე არჩეული) ენა პირველივე ჯერზე ინახება პარამეტრებში
    update_user_preference_fields(user_id, language=st.session_state.lang)
  st.session_state.setdefault("theme", prefs.get("theme") or "auto")

  if not account.subscription.valid:
    render_blocked_screen(user_email, account, st.session_state.lang)
    st.stop()

  is_mobile = detect_is_mobile()
  active_scale = prefs.get("mobile_view_mode", "small") if is_mobile else prefs.get("desktop_view_mode", "medium")
  st.session_state["ui_scale"] = active_scale
  apply_ui_scaling(active_scale)

  render_sidebar_and_navigation(user_id, user_email, account, is_mobile)
