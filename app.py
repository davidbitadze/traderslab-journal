from datetime import datetime
from database import fetch_user_preferences
import streamlit as st
from utils import auth
from utils.sidebar_manager import (
    apply_ui_scaling,
    render_sidebar_sidebar_and_navigation as render_sidebar_nav,
)
from utils.sidebar_manager import render_sidebar_and_navigation

st.set_page_config(
    page_title="Traders Lab - სავაჭრო ჟურნალი", page_icon="📊", layout="wide"
)


def detect_is_mobile():
  """ამოწმებს ბრაუზერის User-Agent-ს მობილურის დასადგენად."""
  try:
    headers = getattr(st.context, "headers", {})
    user_agent = headers.get("User-Agent", "").lower()
    mobile_keywords = ["android", "iphone", "ipad", "ipod", "mobile", "tablet"]
    return any(kw in user_agent for kw in mobile_keywords)
  except Exception:
    return False


# ენის ინიციალიზაცია
if "lang" not in st.session_state:
  st.session_state.lang = "ka"

# ძველი URL-პარამეტრების გასუფთავება
for _old_key in ("saved_email", "saved_uid"):
  if _old_key in st.query_params:
    del st.query_params[_old_key]

# ავტორიზაციის სესიის ინიციალიზაცია
if "user" not in st.session_state:
  st.session_state.user = None

auth.restore_session()
auth.ensure_fresh_session()
auth.flush_cookie_cmd()
if st.query_params.get("debug") == "1":
  auth.render_debug()


def render_auth_screen():
  """ავტორიზაციისა და რეგისტრაციის ფორმა."""
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.title("🔐 Traders Lab - ავტორიზაცია")
    st.write("გთხოვთ გაიარეთ ავტორიზაცია სისტემაში შესასვლელად.")

    tab_login, tab_register = st.tabs(
        ["შესვლა (Login)", "რეგისტრაცია (Register)"]
    )

    with tab_login:
      with st.form("login_form"):
        email = st.text_input("ელ-ფოსტა (Email)", key="login_email")
        password = st.text_input(
            "პაროლი (Password)", type="password", key="login_pass"
        )
        remember_me = st.checkbox("მიმახსოვრე (Remember me)", value=True)
        submit_login = st.form_submit_button("შესვლა", use_container_width=True)

        if submit_login:
          ok, err = auth.login(email, password, remember_me)
          if ok:
            st.rerun()
          else:
            st.error(err)

      pending_email = st.session_state.get("_unconfirmed_email")
      if pending_email and st.button("📧 დადასტურების წერილის ხელახლა გაგზავნა"):
        sent, resend_err = auth.resend_confirmation(pending_email)
        if sent:
          st.success(
              f"წერილი გაიგზავნა მისამართზე {pending_email}. შეამოწმე Spam"
              " საქაღალდეც."
          )
        else:
          st.error(resend_err)

    with tab_register:
      with st.form("register_form"):
        reg_email = st.text_input("ელ-ფოსტა (Email)", key="reg_email")
        reg_password = st.text_input(
            "პაროლი (Password)", type="password", key="reg_pass"
        )
        submit_reg = st.form_submit_button(
            "რეგისტრაცია", use_container_width=True
        )

        if submit_reg:
          ok, err = auth.register(reg_email, reg_password)
          if ok:
            st.success(
                "რეგისტრაცია წარმატებულია! გაგიგზავნეთ წერილი: დააჭირე მასში"
                " დადასტურების ბმულს და შემდეგ შედი სისტემაში."
            )
          else:
            st.error(err or "რეგისტრაცია ვერ მოხერხდა.")


# მთავარი ლოგიკა: ავტორიზაციის შემოწმება
if st.session_state.user is None:
  render_auth_screen()
else:
  user_id = st.session_state.user.id
  user_email = st.session_state.user.email

  if "user_prefs" not in st.session_state:
    prefs = fetch_user_preferences(user_id)
    if prefs:
      st.session_state.user_prefs = prefs
    else:
      st.session_state.user_prefs = {
          "mobile_view_mode": "small",
          "desktop_view_mode": "medium",
          "subscription_expires_at": None,
          "subscription_status": None,
      }

  current_prefs = st.session_state.user_prefs

  # ახალი იუზერის ავტომატური რეგისტრაცია აქტიურ სტატუსზე
  if not current_prefs.get("subscription_status"):
    from database import get_data_client
    try:
      default_update = {
          "user_id": user_id,
          "User_Mail": user_email,
          "subscription_status": "active",
          "credits_balance": float(current_prefs.get("credits_balance", 10.0) or 10.0)
      }
      get_data_client().table("user_preferences").upsert(default_update, on_conflict="user_id").execute()
      current_prefs["subscription_status"] = "active"
      current_prefs["User_Mail"] = user_email
    except Exception:
      pass

  # გამოწერის ვადის შემოწმება
  sub_expires = current_prefs.get("subscription_expires_at")
  sub_status = current_prefs.get("subscription_status")

  is_subscription_valid = True
  if sub_status != "active":
    if sub_expires:
      try:
        exp_date = datetime.fromisoformat(sub_expires.replace("Z", ""))
        if datetime.now() > exp_date:
          is_subscription_valid = False
      except Exception:
        pass
    else:
      is_subscription_valid = False

  lang = st.session_state.get("lang", "ka")

  if not is_subscription_valid:
    from utils.translations import t
    st.sidebar.title(t("settings_title", lang) if "settings_title" in t(lang) else "⚙️ Settings / პარამეტრები")
    st.sidebar.write(f"👤 {user_email}")
    if st.sidebar.button(t("logout", lang), use_container_width=True):
      auth.logout()

    st.error(t("sub_expired_error", lang))
    st.stop()

  # UI მასშტაბისა და თემის ინიციალიზაცია სესიაში
  is_mobile = detect_is_mobile()
  active_scale = (
      current_prefs.get("mobile_view_mode", "small")
      if is_mobile
      else current_prefs.get("desktop_view_mode", "medium")
  )
  st.session_state["ui_scale"] = active_scale
  apply_ui_scaling(active_scale)

  db_lang = current_prefs.get("language") or "ka"
  if "lang" not in st.session_state or st.session_state.lang != db_lang:
    st.session_state.lang = db_lang

  db_theme = current_prefs.get("theme") or "auto"
  if "theme" not in st.session_state:
    st.session_state.theme = db_theme

  # Sidebar-ისა და ნავიგაციის რენდერი მოდულიდან
  render_sidebar_and_navigation(user_id, user_email, current_prefs, is_mobile)
