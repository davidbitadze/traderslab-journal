from database import get_supabase_client
import streamlit as st

supabase = get_supabase_client()


def get_user_credits(user_id: str) -> float:
  """აბრუნებს მომხმარებლის მიმდინარე ქულების ბალანსს."""
  try:
    response = (
        supabase.table("user_preferences")
        .select("credits_balance")
        .eq("user_id", user_id)
        .execute()
    )
    if response.data and len(response.data) > 0:
      balance = response.data[0].get("credits_balance")
      return float(balance) if balance is not None else 0.0
    return 0.0
  except Exception as e:
    st.error(f"ბალანსის წაკითხვის შეცდომა: {e}")
    return 0.0


def check_has_enough_credits(user_id: str, required_credits: float) -> bool:
  """ამოწმებს, ყოფნის თუ არა მომხმარებელს ქულები ოპერაციისთვის."""
  current_balance = get_user_credits(user_id)
  return current_balance >= required_credits


def deduct_credits(user_id: str, amount: float) -> bool:
  """დააკლებს მითითებულ ქულებს მომხმარებლის ბალანსს."""
  current_balance = get_user_credits(user_id)

  if current_balance < amount:
    return False

  new_balance = current_balance - amount
  try:
    supabase.table("user_preferences").update(
        {"credits_balance": new_balance}
    ).eq("user_id", user_id).execute()

    # Session State-შიც მყისიერად ვანახლებთ, რომ UI-მ ეგრევე ასახოს
    if "user_prefs" in st.session_state:
      st.session_state.user_prefs["credits_balance"] = new_balance

    return True
  except Exception as e:
    st.error(f"ქულების ჩამოჭრის შეცდომა: {e}")
    return False


def add_credits(user_id: str, amount: float) -> bool:
  """უმატებს ქულებს მომხმარებლის ბალანსს (მაგ. ყიდვისას ან ბონუსად)."""
  current_balance = get_user_credits(user_id)
  new_balance = current_balance + amount
  try:
    supabase.table("user_preferences").update(
        {"credits_balance": new_balance}
    ).eq("user_id", user_id).execute()

    if "user_prefs" in st.session_state:
      st.session_state.user_prefs["credits_balance"] = new_balance

    return True
  except Exception as e:
    st.error(f"ბალანსის შევსების შეცდომა: {e}")
    return False
