import time
from dataclasses import dataclass
from typing import Optional

import streamlit as st

from database import call_rpc, get_data_client

# ეკრანზე საჩვენებელი ბალანსი სესიაში ინახება და ბაზას მხოლოდ ამდენი წამის შემდეგ ეკითხება.
# ჩამოჭრა/დაბრუნება კი ყოველთვის ბაზის ატომურ ფუნქციებზე მუშაობს.
CREDITS_DISPLAY_TTL = 30

# ბაზის შეცდომის კოდი -> გასაგები ტექსტი
ERROR_TEXTS = {
    "insufficient_credits": "არ გაქვთ საკმარისი ქულები.",
    "subscription_inactive": "გამოწერა აქტიური არ არის.",
    "invalid_amount": "ქულების რაოდენობა არასწორია.",
    "not_authenticated": "ავტორიზაციის შეცდომა.",
}


@dataclass
class ChargeResult:
  ok: bool
  balance: Optional[float] = None
  entry_id: Optional[int] = None
  error: Optional[str] = None  # ადამიანისთვის გასაგები ტექსტი


def _remember_credits(user_id: str, balance: float) -> None:
  st.session_state["_credits_cache"] = (user_id, balance, time.time())
  if "user_prefs" in st.session_state:
    st.session_state.user_prefs["credits_balance"] = balance


def get_user_credits(user_id: str) -> float:
  """აბრუნებს მომხმარებლის მიმდინარე ქულების ბალანსს (ყოველთვის ბაზიდან)."""
  try:
    response = (
        get_data_client().table("user_preferences")
        .select("credits_balance")
        .eq("user_id", user_id)
        .execute()
    )
    if response.data:
      balance = response.data[0].get("credits_balance")
      return float(balance) if balance is not None else 0.0
    return 0.0
  except Exception as e:
    st.error(f"ბალანსის წაკითხვის შეცდომა: {e}")
    return 0.0


def get_user_credits_cached(user_id: str, max_age: float = CREDITS_DISPLAY_TTL) -> float:
  """მხოლოდ ჩვენებისთვის: სესიის ქეშიდან, ბაზაში ზედმეტი მოთხოვნის გარეშე."""
  cached = st.session_state.get("_credits_cache")
  if cached and cached[0] == user_id and time.time() - cached[2] < max_age:
    return cached[1]
  balance = get_user_credits(user_id)
  _remember_credits(user_id, balance)
  return balance


def check_has_enough_credits(user_id: str, required_credits: float) -> bool:
  """სწრაფი წინასწარი შემოწმება (UX-ისთვის). საბოლოო გადაწყვეტილებას ბაზა იღებს."""
  return get_user_credits(user_id) >= required_credits


def charge_credits(user_id: str, amount: float, reason: str) -> ChargeResult:
  """ქულების ჩამოჭრა ბაზის ატომური ფუნქციით spend_credits.

  ბალანსის შემოწმება, ჩამოჭრა და ჟურნალში ჩაწერა ერთ ნაბიჯშია, ამიტომ ორმაგი
  დაჭერითაც ვერ ჩავარდება მინუსში. კლიენტიდან ბალანსის პირდაპირ ჩაწერა აკრძალულია.
  თუ ფუნქცია ბაზაში არ არის (მიგრაცია არ გაშვებულა) — ვუარებთ, არასდროს ვწერთ ბალანსს
  სხვა გზით.
  """
  data, error = call_rpc("spend_credits", {"p_amount": float(amount), "p_reason": reason})
  if error or not isinstance(data, dict):
    return ChargeResult(False, error="ქულების სისტემა ხელმისაწვდომი არ არის. სცადეთ მოგვიანებით.")
  if not data.get("ok"):
    code = data.get("error", "")
    return ChargeResult(False, error=ERROR_TEXTS.get(code, f"ჩამოჭრა ვერ მოხერხდა ({code})."))
  balance = float(data["balance"])
  _remember_credits(user_id, balance)
  return ChargeResult(True, balance=balance, entry_id=data.get("entry_id"))


def refund_charge(user_id: str, charge: ChargeResult) -> bool:
  """უკან უბრუნებს მხოლოდ ამ კონკრეტულ ჩამოჭრას (ერთხელ, 15 წუთის განმავლობაში)."""
  if not charge or not charge.ok or charge.entry_id is None:
    return False
  data, error = call_rpc("refund_spend", {"p_entry_id": int(charge.entry_id)})
  if error or not isinstance(data, dict) or not data.get("ok"):
    return False
  _remember_credits(user_id, float(data["balance"]))
  return True
