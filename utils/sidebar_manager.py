import streamlit as st
from database import get_data_client
from utils.translations import t
from views.admin import render_admin_view
from views.analytics import render_analytics_view
from views.journal import render_journal_view
from views.settings import render_settings_view


def apply_ui_scaling(scale_mode):
  """ადგენს CSS სტილებს არჩეული მასშტაბის მიხედვით."""
  styles = {
      "small": """
            <style>
                html, body, [class*="css"] { font-size: 13px !important; }
                .stButton button { padding: 0.25rem 0.5rem !important; font-size: 12px !important; }
            </style>
        """,
      "medium": """
            <style>
                html, body, [class*="css"] { font-size: 15px !important; }
            </style>
        """,
      "large": """
            <style>
                html, body, [class*="css"] { font-size: 17px !important; }
            </style>
        """,
  }
  st.markdown(styles.get(scale_mode, styles["medium"]), unsafe_allow_html=True)


def apply_theme_styles(theme_mode):
  """თემის CSS სტილების ინექცია."""
  if theme_mode == "light":
    css = """
        <style>
            [data-testid="stAppViewContainer"] { background-color: #f8f9fa; color: #212529; }
            [data-testid="stSidebar"] { background-color: #e9ecef; }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  elif theme_mode == "dark":
    css = """
        <style>
            [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #fafafa; }
            [data-testid="stSidebar"] { background-color: #1a1c23; color: #fafafa; }
            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #1a1c23 !important;
                color: #fafafa !important;
                border-color: #333333 !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def is_user_admin(user_email, current_prefs):
  """ამოწმებს არის თუ არა იუზერი ადმინი (ბაზის სვეტით ან ფოლბექით)."""
  # ჯერ ვამოწმებთ ბაზაში სვეტს (is_admin ან role == 'admin')
  db_is_admin = current_prefs.get("is_admin") or current_prefs.get("role") == "admin"
  if db_is_admin:
    return True
  
  # ფოლბექი მთავარი შემქმნელის ელ-ფოსტაზე (სურვილისამებრ შეგიძლია შეცვალო ან ამოიღო)
  DEFAULT_ADMINS = ["eufrazio@yandex.ru"]
  return user_email in DEFAULT_ADMINS


def render_sidebar_and_navigation(user_id, user_email, current_prefs, is_mobile):
  """მართავს გვერდითა მენიუს, პრეფერენსებს და ნავიგაციას."""
  lang = st.session_state.get("lang", "ka")

  # Sidebar სათაური და პროფილი
  st.sidebar.title(t("settings_title", lang) if "settings_title" in t(lang) else "⚙️ Settings / პარამეტრები")
  st.sidebar.write(f"👤 {user_email}")
  device_label = "📱 მობილური" if is_mobile else "💻 დესკტოპი"
  active_scale = st.session_state.get("ui_scale", "medium")
  st.sidebar.caption(f"{t('device', lang)}: **{device_label}** | {t('scale', lang)}: **{active_scale}**")

  from utils import auth
  if st.sidebar.button(t("logout", lang), use_container_width=True, key="logout_btn"):
    auth.logout()

  # ენის არჩევანი
  selected_lang = st.sidebar.selectbox(
      "Language / ენა",
      options=["ka", "en"],
      format_func=lambda x: "🇬🇪 ქართული" if x == "ka" else "🇬🇧 English",
      index=0 if lang == "ka" else 1,
      key="global_lang_select"
  )

  if selected_lang != lang:
    st.session_state.lang = selected_lang
    try:
      get_data_client().table("user_preferences").update({"language": selected_lang}).eq("user_id", user_id).execute()
    except Exception:
      pass
    st.rerun()

  # თემის არჩევანი
  theme_options = ["auto", "dark", "light"]
  theme_labels = {
      "auto": t("theme_auto", lang),
      "dark": t("theme_dark", lang),
      "light": t("theme_light", lang)
  }

  current_theme = st.session_state.get("theme", "auto")
  current_theme_index = theme_options.index(current_theme) if current_theme in theme_options else 0
  
  selected_theme = st.sidebar.selectbox(
      t("theme_label", lang),
      options=theme_options,
      format_func=lambda x: theme_labels[x],
      index=current_theme_index,
      key="global_theme_select"
  )

  if selected_theme != current_theme:
    st.session_state.theme = selected_theme
    try:
      get_data_client().table("user_preferences").update({"theme": selected_theme}).eq("user_id", user_id).execute()
    except Exception:
      pass
    st.rerun()

  apply_theme_styles(st.session_state.get("theme", "auto"))

  # ნავიგაციის მენიუ
  st.sidebar.title(t("nav_header", lang))
  
  menu_options = [
      t("journal", lang),
      t("analytics", lang),
      t("settings", lang),
  ]
  
  # დინამიური ადმინ შემოწმება ბაზიდან
  if is_user_admin(user_email, current_prefs):
    menu_options.append(t("admin", lang))

  selected_menu = st.sidebar.selectbox("აირჩიეთ გვერდი", menu_options, key="main_navigation_select", label_visibility="collapsed")

  # გვერდების რენდერი
  if selected_menu in ["📊 სავაჭრო ჟურნალი", "📊 Trade Journal"]:
    render_journal_view(lang)
  elif selected_menu in ["📈 ანალიტიკა", "📈 Analytics"]:
    render_analytics_view(lang)
  elif selected_menu in ["⚙️ პარამეტრები და ცნობარები", "⚙️ Settings & References"]:
    render_settings_view(lang)
  elif selected_menu in ["🛡️ ადმინისტრაცია", "🛡️ Administration"]:
    render_admin_view()
