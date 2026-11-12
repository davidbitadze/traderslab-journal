import pandas as pd
import streamlit as st
from database import (
    admin_update_user_credits,
    admin_update_user_role,
    fetch_all_user_preferences,
)


def render_admin_view():
  user_email = (
      st.session_state.user.email
      if hasattr(st.session_state, "user") and st.session_state.user
      else ""
  )

  # უსაფრთხოების შემოწმება ბაზის მიხედვით (ან მყარი მეილით)
  df_users = fetch_all_user_preferences()
  current_user_row = (
      df_users[df_users["User_Mail"] == user_email]
      if not df_users.empty
      else pd.DataFrame()
  )
  is_db_admin = (
      not current_user_row.empty
      and current_user_row.iloc[0].get("role") == "admin"
  )
  fallback_admin = user_email == "eufrazio@yandex.ru"

  if not is_db_admin and not fallback_admin:
    st.error("⛔ თქვენ არ გაქვთ ადმინისტრატორის უფლებები.")
    return

  st.title("🛡️ ადმინისტრატორის პანელი")
  st.caption(f"ავტორიზებული ადმინი: **{user_email}**")

  if df_users.empty:
    st.info("მომხმარებლების ჩანაწერები ჯერ არ არის.")
    return

  st.markdown("### 👥 მომხმარებლების მართვა და როლები")

  # ძირითადი ცხრილის გამოჩენა (როლის სვეტითურთ)
  display_df = df_users.copy()
  cols_to_show = [
      c
      for c in [
          "user_id",
          "User_Mail",
          "role",
          "credits_balance",
          "subscription_status",
          "created_at",
      ]
      if c in display_df.columns
  ]
  st.dataframe(display_df[cols_to_show], use_container_width=True)

  st.divider()

  # --- მომხმარებლის როლის შეცვლა ---
  st.markdown("### 🔑 მომხმარებლის როლის მართვა")
  users_list_role = []
  for _, row in df_users.iterrows():
    u_id = row.get("user_id")
    u_mail = row.get("User_Mail") or u_id[:8]
    u_role = row.get("role") or "user"
    users_list_role.append((u_id, f"{u_mail} (როლი: {u_role})"))

  selected_role_tuple = st.selectbox(
      "აირჩიეთ მომხმარებელი როლის შესაცვლელად",
      options=users_list_role,
      format_func=lambda x: x[1],
      key="admin_role_select",
  )

  if selected_role_tuple:
    target_u_id = selected_role_tuple[0]
    target_row = df_users[df_users["user_id"] == target_u_id].iloc[0]
    current_role = target_row.get("role") or ""

    col_r1, col_r2 = st.columns(2)
    with col_r1:
      new_role_input = st.selectbox(
          "ახალი როლი",
          options=["user", "admin"],
          index=0 if current_role != "admin" else 1,
          key=f"role_box_{target_u_id}",
      )
    with col_r2:
      st.write("")  # გასწორებისთვის
      st.write("")
      if st.button("💾 როლის შენახვა", use_container_width=True):
        if admin_update_user_role(target_u_id, new_role_input):
          st.success(f"მომხმარებლის როლი წარმატებით შეიცვალა ({new_role_input})-ზე!")
          st.rerun()

  st.divider()

  # --- ქულების შევსების / რედაქტირების ფორმა ---
  st.markdown("### 💳 კრედიტების / ქულების ჩარიცხვა")

  users_list = []
  for _, row in df_users.iterrows():
    u_id = row.get("user_id")
    u_mail = row.get("User_Mail") or u_id[:8]
    users_list.append(
        (
            u_id,
            f"{u_mail} (მიმდინარე: {row.get('credits_balance', 0):g} ქულა)",
        )
    )

  selected_user_tuple = st.selectbox(
      "აირჩიეთ მომხმარებელი ბალანსისთვის",
      options=users_list,
      format_func=lambda x: x[1],
      key="admin_user_select",
  )

  if selected_user_tuple:
    target_user_id = selected_user_tuple[0]
    current_row = df_users[df_users["user_id"] == target_user_id].iloc[0]
    curr_credits = float(current_row.get("credits_balance", 0.0))

    col_c1, col_c2 = st.columns(2)
    with col_c1:
      add_amount = st.number_input(
          "ქულების დამატება (მაგ. 50)", value=10.0, step=5.0
      )
      if st.button("➕ ქულების ჩარიცხვა", use_container_width=True):
        new_bal = curr_credits + add_amount
        if admin_update_user_credits(target_user_id, new_bal):
          st.success(f"წარმატებით დაემატა! ახალი ბალანსი: {new_bal:g}")
          st.rerun()

    with col_c2:
      exact_amount = st.number_input(
          "ზუსტი ბალანსის მითითება", value=curr_credits, step=1.0
      )
      if st.button("✏️ ბალანსის განახლება", use_container_width=True):
        if admin_update_user_credits(target_user_id, exact_amount):
          st.success(f"ბალანსი განახლდა: {exact_amount:g}")
          st.rerun()
