from datetime import datetime
from database import fetch_user_preferences
import streamlit as st
from utils import auth
from utils.translations import t
from views.admin import render_admin_view
from views.analytics import render_analytics_view
from views.journal import render_journal_view
from views.settings import render_settings_view

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


def apply_ui_scaling(scale_mode):
  """ადგენს CSS სტილებს არჩეული მასშტაბის მიხედვით."""
  styles = {
      "small": """
            <style>
                html, body, [class*="css"] {
                    font-size: 13px !important;
                }
                .stButton button {
                    padding: 0.25rem 0.5rem !important;
                    font-size: 12px !important;
                }
            </style>
        """,
      "medium": """
            <style>
                html, body, [class*="css"] {
                    font-size: 15px !important;
                }
            </style>
        """,
      "large": """
            <style>
                html, body, [class*="css"] {
                    font-size: 17px !important;
                }
            </style>
        """,
  }
  css_code = styles.get(scale_mode, styles["medium"])
  st.markdown(css_code, unsafe_allow_html=True)


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

  # თუ ახალი იუზერია და სვეტები ცარიელია, ავტომატურად ვურეგისტრირებთ active სტატუსს
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

  if not is_subscription_valid:
    st.sidebar.title("⚙️ Settings / პარამეტრები")
    st.sidebar.write(f"👤 {user_email}")
    if st.sidebar.button("🚪 გასვლა (Logout)", use_container_width=True):
      auth.logout()

    st.error(
        "⚠️ **თქვენი გამოწერის ვადა ამოწურულია ან აქტიური არ არის.**"
        " სავაჭრო ჟურნალსა და ანალიტიკაზე წვდომისთვის გთხოვთ განაახლოთ"
        " გამოწერა."
    )
    st.stop()

  # UI მასშტაბი
  is_mobile = detect_is_mobile()
  active_scale = (
      current_prefs.get("mobile_view_mode", "small")
      if is_mobile
      else current_prefs.get("desktop_view_mode", "medium")
  )
  st.session_state["ui_scale"] = active_scale
  apply_ui_scaling(active_scale)

  # --- ენისა და თემის ინიციალიზაცია ბაზიდან ---
  db_lang = current_prefs.get("language") or "ka"
  if "lang" not in st.session_state:
    st.session_state.lang = db_lang

  db_theme = current_prefs.get("theme") or "dark"
  if "theme" not in st.session_state:
    st.session_state.theme = db_theme

  # Sidebar მართვა
  st.sidebar.title("⚙️ Settings / პარამეტრები")
  st.sidebar.write(f"👤 {user_email}")
  device_label = "📱 მობილური" if is_mobile else "💻 დესკტოპი"
  st.sidebar.caption(f"მოწყობილობა: **{device_label}** | ზომა: **{active_scale}**")

  if st.sidebar.button("🚪 გასვლა (Logout)", use_container_width=True, key="logout_btn"):
    auth.logout()

  # Sidebar: ენის არჩევანი (უნიკალური key-ით)
  selected_lang = st.sidebar.selectbox(
      "Language / ენა",
      options=["ka", "en"],
      format_func=lambda x: "🇬🇪 ქართული" if x == "ka" else "🇬🇧 English",
      index=0 if st.session_state.lang == "ka" else 1,
      key="global_lang_select"
  )

  if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    try:
      from database import get_data_client
      get_data_client().table("user_preferences").update({"language": selected_lang}).eq("user_id", user_id).execute()
    except Exception:
      pass
    st.rerun()

  lang = st.session_state.lang

  # Sidebar: თემის არჩევანი (უნიკალური key-ით)
  theme_options = ["dark", "light"]
  theme_labels = {
      "dark": t("theme_dark", lang) if "theme_dark" in globals() or True else "🌙 Dark",
      "light": t("theme_light", lang) if "theme_light" in globals() or True else "☀️ Light"
  }

  current_theme_index = 0 if st.session_state.theme == "dark" else 1
  selected_theme = st.sidebar.selectbox(
      t("theme_label", lang) if "theme_label" in globals() or True else "🎨 Theme / თემა",
      options=theme_options,
      format_func=lambda x: theme_labels[x],
      index=current_theme_index,
      key="global_theme_select"
  )

  if selected_theme != st.session_state.theme:
    st.session_state.theme = selected_theme
    try:
      from database import get_data_client
      get_data_client().table("user_preferences").update({"theme": selected_theme}).eq("user_id", user_id).execute()
    except Exception:
      pass
    st.rerun()

  # სტილების ფუნქცია
  def apply_theme_styles(theme_mode):
    if theme_mode == "light":
      css = """
          <style>
              [data-testid="stAppViewContainer"] {
                  background-color: #ffffff;
                  color: #111111;
              }
              [data-testid="stSidebar"] {
                  background-color: #f0f2f6;
                  color: #111111;
              }
              .stMarkdown, p, span, label {
                  color: #111111 !important;
              }
          </style>
      """
    else:
      css = """
          <style>
              [data-testid="stAppViewContainer"] {
                  background-color: #0e1117;
                  color: #fafafa;
              }
              [data-testid="stSidebar"] {
                  background-color: #1a1c23;
                  color: #fafafa;
              }
          </style>
      """
    st.markdown(css, unsafe_allow_html=True)

  apply_theme_styles(st.session_state.theme)

  # ნავიგაციის მენიუ
  st.sidebar.title(t("nav_header", lang) if "nav_header" in globals() else "ნავიგაცია")
  
  menu_options = [
      "📊 სავაჭრო ჟურნალი",
      "📈 ანალიტიკა",
      "⚙️ პარამეტრები და ცნობარები",
  ]
  
  ADMIN_EMAILS = [
      "eufrazio@yandex.ru"
  ]
  if user_email in ADMIN_EMAILS:
    menu_options.append("🛡️ ადმინისტრაცია")

  selected_menu = st.sidebar.radio("აირჩიეთ გვერდი", menu_options, key="main_navigation_radio")

  if selected_menu == "📊 სავაჭრო ჟურნალი":
    render_journal_view(lang)
  elif selected_menu == "📈 ანალიტიკა":
    render_analytics_view(lang)
  elif selected_menu == "⚙️ პარამეტრები და ცნობარები":
    render_settings_view(lang)
  elif selected_menu == "🛡️ ადმინისტრაცია":
    render_admin_view()
