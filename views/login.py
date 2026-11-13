import streamlit as st

from utils import auth


def render_auth_screen():
  """ავტორიზაციისა და რეგისტრაციის ფორმა."""
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    st.title("🔐 Traders Lab - ავტორიზაცია")
    st.write("გთხოვთ გაიარეთ ავტორიზაცია სისტემაში შესასვლელად.")

    tab_login, tab_register = st.tabs(["შესვლა (Login)", "რეგისტრაცია (Register)"])

    with tab_login:
      with st.form("login_form"):
        email = st.text_input("ელ-ფოსტა (Email)", key="login_email")
        password = st.text_input("პაროლი (Password)", type="password", key="login_pass")
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
              f"წერილი გაიგზავნა მისამართზე {pending_email}. შეამოწმე Spam საქაღალდეც."
          )
        else:
          st.error(resend_err)

    with tab_register:
      with st.form("register_form"):
        reg_email = st.text_input("ელ-ფოსტა (Email)", key="reg_email")
        reg_password = st.text_input("პაროლი (Password)", type="password", key="reg_pass")
        submit_reg = st.form_submit_button("რეგისტრაცია", use_container_width=True)

        if submit_reg:
          ok, err = auth.register(reg_email, reg_password)
          if ok:
            st.success(
                "რეგისტრაცია წარმატებულია! გაგიგზავნეთ წერილი: დააჭირე მასში"
                " დადასტურების ბმულს და შემდეგ შედი სისტემაში."
            )
          else:
            st.error(err or "რეგისტრაცია ვერ მოხერხდა.")
