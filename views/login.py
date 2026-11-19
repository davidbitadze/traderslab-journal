import streamlit as st

from i18n import available_languages, t
from utils import auth


def _language_selector():
  """ენის არჩევა შესვლამდეც: პირველად ბრაუზერის ენა იღება (app.py), აქ შეიძლება შეცვლა."""
  languages = available_languages()
  codes = [code for code, _ in languages]
  labels = dict(languages)
  current = st.session_state.get("lang", "ka")
  selected = st.selectbox(
      "Language / ენა",
      options=codes,
      format_func=lambda code: labels[code],
      index=codes.index(current) if current in codes else 0,
      key="login_lang_select",
  )
  if selected != current:
    st.session_state.lang = selected
    st.rerun()


def render_auth_screen():
  """ავტორიზაციისა და რეგისტრაციის ფორმა."""
  col1, col2, col3 = st.columns([1, 2, 1])
  with col2:
    _language_selector()
    lang = st.session_state.get("lang", "ka")
    st.title(t("auth_title", lang))
    st.write(t("auth_subtitle", lang))

    tab_login, tab_register = st.tabs([t("tab_login", lang), t("tab_register", lang)])

    with tab_login:
      with st.form("login_form"):
        email = st.text_input(t("email_label", lang), key="login_email")
        password = st.text_input(t("pass_label", lang), type="password", key="login_pass")
        remember_me = st.checkbox(t("remember_me", lang), value=True)
        submit_login = st.form_submit_button(t("login_btn", lang), use_container_width=True)

        if submit_login:
          ok, err = auth.login(email, password, remember_me)
          if ok:
            st.rerun()
          else:
            st.error(err)

      pending_email = st.session_state.get("_unconfirmed_email")
      if pending_email and st.button(t("resend_email", lang)):
        sent, resend_err = auth.resend_confirmation(pending_email)
        if sent:
          st.success(t("confirmation_sent", lang, email=pending_email))
        else:
          st.error(resend_err)

    with tab_register:
      with st.form("register_form"):
        reg_email = st.text_input(t("email_label", lang), key="reg_email")
        reg_password = st.text_input(t("pass_label", lang), type="password", key="reg_pass")
        submit_reg = st.form_submit_button(t("register_btn", lang), use_container_width=True)

        if submit_reg:
          ok, err = auth.register(reg_email, reg_password)
          if ok:
            st.success(t("reg_success", lang))
          else:
            st.error(err or t("register_failed", lang))
