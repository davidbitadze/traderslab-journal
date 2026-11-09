from datetime import datetime
from database import fetch_user_preferences
import streamlit as st
from utils import auth
from utils.translations import t
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

# ძველი, დაუცველი URL-პარამეტრები (?saved_email=&saved_uid=) აღარ გამოიყენება: ვშლით
for _old_key in ("saved_email", "saved_uid"):
  if _old_key in st.query_params:
    del st.query_params[_old_key]

# ავტორიზაციის სესიის ინიციალიზაცია
if "user" not in st.session_state:
  st.session_state.user = None

auth.restore_session()  # რეფრეშის შემდეგ: cookie-ს refresh token-ით სესიის აღდგენა
auth.ensure_fresh_session()
# cookie-ს ჩაწერა/წაშლა ბოლოს: restore-ის ახალი (rotated) token იმავე გაშვებაში უნდა ჩაიწეროს
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

    # --- შესვლა ---
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
            st.error(f"შესვლის შეცდომა: {err}")

    # --- რეგისტრაცია ---
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
            st.success("რეგისტრაცია წარმატებულია! გთხოვთ შეამოწმოთ მეილი.")
          else:
            st.error(f"რეგისტრაციის შეცდომა: {err}" if err else "რეგისტრაცია ვერ მოხერხდა")


# მთავარი ლოგიკა: თუ მომხმარებელი არ არის ავტორიზებული
if st.session_state.user is None:
  render_auth_screen()
else:
  user_id = st.session_state.user.id
  user_email = st.session_state.user.email

  # 1. ბაზიდან პრეფერენციებისა და გამოწერის მონაცემების წამოღება
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

  # --- გამოწერისა და წვდომის კონტროლი ---
  # თუ ბაზაში სვეტი ცარიელია (NULL) ან ვადა გასულია, ვბლოკავთ წვდომას
  sub_expires = current_prefs.get("subscription_expires_at")
  sub_status = current_prefs.get("subscription_status")

  is_subscription_valid = True  # საწყისი დაშვება

  if not sub_expires or sub_status != "active":
    is_subscription_valid = False
  else:
    try:
      # ვამოწმებთ მიმდინარე თარიღს გამოწერის ვადასთან
      exp_date = datetime.fromisoformat(sub_expires.replace("Z", ""))
      if datetime.now() > exp_date:
        is_subscription_valid = False
    except Exception:
      pass

  # თუ გამოწერა არ არის აქტიური ან ვადა გავიდა
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
    st.stop()  # აჩერებს დანარჩენი გვერდის რენდერს სანამ გადახდა არ განახლდება

  # 2. მოწყობილობის იდენტიფიკაცია და UI მასშტაბი
  is_mobile = detect_is_mobile()
  active_scale = (
      current_prefs.get("mobile_view_mode", "small")
      if is_mobile
      else current_prefs.get("desktop_view_mode", "medium")
  )
  st.session_state["ui_scale"] = active_scale
  apply_ui_scaling(active_scale)

  # --- ავტორიზებული და აქტიურ-გამოწერიანი მომხმარებლის ინტერფეისი ---
  st.sidebar.title("⚙️ Settings / პარამეტრები")
  st.sidebar.write(f"👤 {user_email}")
  device_label = "📱 მობილური" if is_mobile else "💻 დესკტოპი"
  st.sidebar.caption(f"მოწყობილობა: **{device_label}** | ზომა: **{active_scale}**")

  if st.sidebar.button("🚪 გასვლა (Logout)", use_container_width=True):
    auth.logout()

  selected_lang = st.sidebar.selectbox(
      "Language / ენა",
      options=["ka", "en"],
      format_func=lambda x: "🇬🇪 ქართული" if x == "ka" else "🇬🇧 English",
      index=0 if st.session_state.lang == "ka" else 1,
  )

  if selected_lang != st.session_state.lang:
    st.session_state.lang = selected_lang
    st.rerun()

  lang = st.session_state.lang

  # მთავარი მენიუ
  st.sidebar.title(t("nav_header", lang))
  menu = st.sidebar.selectbox(
      "აირჩიეთ გვერდი",
      ["📊 სავაჭრო ჟურნალი", "⚙️ სეტინგები და ცნობარები", "📈 ანალიტიკა"],
  )

  if menu == "📊 სავაჭრო ჟურნალი":
    render_journal_view(lang)

  elif menu == "⚙️ სეტინგები და ცნობარები":
    render_settings_view(lang)

  elif menu == "📈 ანალიტიკა":
    render_analytics_view(lang)
