import streamlit as st
from database import fetch_user_preferences, get_supabase_client
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

# Supabase კლიენტის ინიციალიზაცია
supabase = get_supabase_client()

# ავტორიზაციის სესიის შემოწმება
if "user" not in st.session_state:
  st.session_state.user = None

# ვცდილობთ აღვადგინოთ სესია Supabase-ის ავტომატური ტოკენიდან ან სესიიდან
if st.session_state.user is None:
  try:
    session_response = supabase.auth.get_session()
    if session_response and session_response.session:
      st.session_state.user = session_response.session.user
  except Exception:
    pass


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
        submit_login = st.form_submit_button("შესვლა", use_container_width=True)

        if submit_login:
          try:
            response = supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            if response.user:
              st.session_state.user = response.user
              st.success("წარმატებით შეხვედით სისტემაში!")
              st.rerun()
          except Exception as e:
            st.error(f"შესვლის შეცდომა: {e}")

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
          try:
            response = supabase.auth.sign_up(
                {"email": reg_email, "password": reg_password}
            )
            if response.user:
              st.success(
                  "რეგისტრაცია წარმატებულია! გთხოვთ შეამოწმოთ მეილი."
              )
          except Exception as e:
            st.error(f"რეგისტრაციის შეცდომა: {e}")


# მთავარი ლოგიკა: თუ მომხმარებელი არ არის ავტორიზებული
if st.session_state.user is None:
  render_auth_screen()
else:
  user_id = st.session_state.user.id
  user_email = st.session_state.user.email

  # 1. მოწყობილობის იდენტიფიკაცია
  is_mobile = detect_is_mobile()

  # 2. ბაზიდან პრეფერენციების წამოღება
  if "user_prefs" not in st.session_state:
    prefs = fetch_user_preferences(user_id)
    if prefs:
      st.session_state.user_prefs = prefs
    else:
      st.session_state.user_prefs = {
          "mobile_view_mode": "small",
          "desktop_view_mode": "medium",
      }

  # 3. შესაბამისი რეჟიმის შერჩევა და CSS-ის მიწოდება
  current_prefs = st.session_state.user_prefs
  active_scale = (
      current_prefs.get("mobile_view_mode", "small")
      if is_mobile
      else current_prefs.get("desktop_view_mode", "medium")
  )
  apply_ui_scaling(active_scale)

  # --- ავტორიზებული მომხმარებლის ინტერფეისი ---
  st.sidebar.title("⚙️ Settings / პარამეტრები")
  st.sidebar.write(f"👤 {user_email}")
  device_label = "📱 მობილური" if is_mobile else "💻 დესკტოპი"
  st.sidebar.caption(f"მოწყობილობა: **{device_label}** | ზომა: **{active_scale}**")

  if st.sidebar.button("🚪 გასვლა (Logout)", use_container_width=True):
    try:
      supabase.auth.sign_out()
    except Exception:
      pass
    st.session_state.user = None
    if "user_prefs" in st.session_state:
      del st.session_state["user_prefs"]
    if "saved_user" in st.query_params:
      del st.query_params["saved_user"]
    st.rerun()

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
