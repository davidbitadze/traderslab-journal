import streamlit as st
from database import get_supabase_client
from utils.translations import t
from views.analytics import render_analytics_view
from views.journal import render_journal_view
from views.settings import render_settings_view

st.set_page_config(
    page_title="Traders Lab - სავაჭრო ჟურნალი", page_icon="📊", layout="wide"
)

# ენის ინიციალიზაცია
if "lang" not in st.session_state:
  st.session_state.lang = "ka"

# სესიის ინიციალიზაცია ავტორიზაციისთვის
if "user" not in st.session_state:
  st.session_state.user = None


def render_auth_screen():
  """ავტორიზაციისა და რეგისტრაციის მარტივი ფორმა"""
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.title("🔐 Traders Lab - ავტორიზაცია")
    st.write("გთხოვთ გაიარეთ ავტორიზაცია სისტემაში შესასვლელად.")

    tab_login, tab_register = st.tabs(["შესვლა (Login)", "რეგისტრაცია (Register)"])

    supabase = get_supabase_client()

    # --- შესვლა ---
    with tab_login:
      with st.form("login_form"):
        email = st.text_input("ელ-ფოსტა (Email)", key="login_email")
        password = st.text_input("პაროლი (Password)", type="password", key="login_pass")
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
        reg_password = st.text_input("პაროლი (Password)", type="password", key="reg_pass")
        submit_reg = st.form_submit_button("რეგისტრაცია", use_container_width=True)

        if submit_reg:
          try:
            response = supabase.auth.sign_up(
                {"email": reg_email, "password": reg_password}
            )
            if response.user:
              st.success("რეგისტრაცია წარმატებულია! გთხოვთ შეამოწმოთ მეილი (ასეთის არსებობის შემთხვევაში) ან გადახვიდეთ შესვლის ფანჯარაში.")
          except Exception as e:
            st.error(f"რეგისტრაციის შეცდომა: {e}")


# მთავარი ლოგიკა: თუ მომხმარებელი არ არის ავტორიზებული, ვაჩვენებთ ლოგინს
if st.session_state.user is None:
  render_auth_screen()
else:
  # --- ავტორიზებული მომხმარებლის ინტერფეისი ---
  user_email = st.session_state.user.email

  st.sidebar.title("⚙️ Settings / პარამეტრები")
  st.sidebar.write(f"👤 {user_email}")
  
  if st.sidebar.button("🚪 გასვლა (Logout)", use_container_width=True):
    try:
      supabase = get_supabase_client()
      supabase.auth.sign_out()
    except Exception:
      pass
    st.session_state.user = None
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
