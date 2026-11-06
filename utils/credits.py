import time

from database import get_supabase_client
import streamlit as st

supabase = get_supabase_client()

# ეკრანზე საჩვენებელი ბალანსი სესიაში ინახება და ბაზას მხოლოდ ამდენი წამის შემდეგ ეკითხება.
# ჩამოჭრა/შევსება კი ყოველთვის ბაზის ახალ მონაცემზე მუშაობს (იხ. get_user_credits).
CREDITS_DISPLAY_TTL = 30


def _remember_credits(user_id: str, balance: float) -> None:
  st.session_state["_credits_cache"] = (user_id, balance, time.time())


def get_user_credits(user_id: str) -> float:
  """აბრუნებს მომხმარებლის მიმდინარე ქულების ბალანსს (ყოველთვის ბაზიდან)."""
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


def get_user_credits_cached(
    user_id: str, max_age: float = CREDITS_DISPLAY_TTL
) -> float:
  """მხოლოდ ჩვენებისთვის: სესიის ქეშიდან, ბაზაში ზედმეტი მოთხოვნის გარეშე."""
  cached = st.session_state.get("_credits_cache")
  if cached and cached[0] == user_id and time.time() - cached[2] < max_age:
    return cached[1]
  balance = get_user_credits(user_id)
  _remember_credits(user_id, balance)
  return balance


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
    _remember_credits(user_id, new_balance)

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
    _remember_credits(user_id, new_balance)

    return True
  except Exception as e:
    st.error(f"ბალანსის შევსების შეცდომა: {e}")
    return False
