"""გვერდითა პანელი და ნავიგაცია."""

import streamlit as st

from database import update_user_preference_fields
from utils import auth
from utils.theme import apply_theme_styles
from utils.translations import t
from views.admin import render_admin_view
from views.analytics import render_analytics_view
from views.journal import render_journal_view
from views.settings import render_settings_view

# გვერდები: გასაღები -> (მენიუს თარგმანის გასაღები, ფუნქცია, მხოლოდ ადმინისთვის?)
PAGES = {
    "journal": ("journal", render_journal_view, False),
    "analytics": ("analytics", render_analytics_view, False),
    "settings": ("settings", render_settings_view, False),
    "admin": ("admin", render_admin_view, True),
}


def _language_picker(user_id, lang):
  selected = st.sidebar.selectbox(
      t("language", lang) if "language" in t(lang) else "Language / ენა",
      options=["ka", "en"],
      format_func=lambda x: "🇬🇪 ქართული" if x == "ka" else "🇬🇧 English",
      index=0 if lang == "ka" else 1,
      key="global_lang_select",
  )
  if selected != lang:
    st.session_state.lang = selected
    update_user_preference_fields(user_id, language=selected)
    st.rerun()


def _theme_picker(user_id, lang):
  options = ["auto", "dark", "light"]
  labels = {k: t(f"theme_{k}", lang) for k in options}
  current = st.session_state.get("theme", "auto")
  selected = st.sidebar.selectbox(
      t("theme_label", lang),
      options=options,
      format_func=lambda x: labels[x],
      index=options.index(current) if current in options else 0,
      key="global_theme_select",
  )
  if selected != current:
    st.session_state.theme = selected
    update_user_preference_fields(user_id, theme=selected)
    st.rerun()
  apply_theme_styles(st.session_state.get("theme", "auto"))


def render_sidebar_and_navigation(user_id, user_email, account, is_mobile):
  """გვერდითა მენიუ, ენა, თემა და არჩეული გვერდის ჩვენება."""
  lang = st.session_state.get("lang", "ka")

  st.sidebar.title(t("settings_title", lang))
  st.sidebar.write(f"👤 {user_email}")
  
  device_label = t("mobile_device", lang) if is_mobile else t("desktop_device", lang)
  active_scale = st.session_state.get("ui_scale", "medium")
  st.sidebar.caption(f"{t('device', lang)}: **{device_label}** | {t('scale', lang)}: **{active_scale}**")

  expires_at = account.subscription.expires_at
  if expires_at:
    st.sidebar.caption(
        f"🗓️ {t('subscription_until', lang)}: **{expires_at.strftime('%Y-%m-%d')}**"
        f" ({account.subscription.days_left} {t('days_short', lang)})"
    )

  if st.sidebar.button(t("logout", lang), use_container_width=True, key="logout_btn"):
    auth.logout()

  _language_picker(user_id, lang)
  _theme_picker(user_id, lang)

  st.sidebar.title(t("nav_header", lang))
  
  # ადმინის გვერდი მხოლოდ ბაზაში დადასტურებულ ადმინს ეჩვენება
  visible = [key for key, (_, _, admin_only) in PAGES.items() if account.is_admin or not admin_only]
  
  page = st.sidebar.selectbox(
      t("select_page", lang),
      visible,
      format_func=lambda key: t(PAGES[key][0], lang),
      key="main_navigation_select",
      label_visibility="collapsed",
  )
  PAGES[page][1](lang)
