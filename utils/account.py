"""მომხმარებლის ანგარიშის მდგომარეობა: პარამეტრები, გამოწერა, როლი.

ერთი ადგილი, სადაც ვწყვეტთ „შეუძლია თუ არა ამ მომხმარებელს აპის გამოყენება“.
პარამეტრები სესიაში ინახება და პერიოდულად ახლდება, რომ ადმინის ცვლილება
(გაუქმება, ვადის გაგრძელება, როლი) მიმდინარე სესიაზეც გავრცელდეს.
"""

import time
from dataclasses import dataclass
from typing import Optional

import streamlit as st

from database import ensure_user_preferences, fetch_my_staff_role, fetch_user_preferences
from utils.subscription import SubscriptionState, evaluate

PREFS_REFRESH_SECONDS = 300
DEFAULT_PREFS = {"mobile_view_mode": "small", "desktop_view_mode": "medium"}


@dataclass
class Account:
  prefs: dict
  subscription: SubscriptionState
  staff_role: Optional[str]  # 'admin' | 'mentor' | None
  load_failed: bool = False

  @property
  def is_admin(self) -> bool:
    return self.staff_role == "admin"


def _load_prefs(user_id):
  # რიგი არ არსებობს (ძველი ანგარიში) -> ბაზის ფუნქცია ქმნის ნაგულისხმევს (10 ქულა, active)
  return fetch_user_preferences(user_id) or ensure_user_preferences()


def load_account(user_id) -> Account:
  """ანგარიშის მდგომარეობა; ბაზას ეკითხება სესიაში ერთხელ და შემდეგ ყოველ 5 წუთში."""
  state = st.session_state
  stale = time.time() - state.get("_prefs_loaded_at", 0) > PREFS_REFRESH_SECONDS

  if "user_prefs" not in state or stale:
    fresh = _load_prefs(user_id)
    if fresh:
      merged = dict(state.get("user_prefs") or {})
      merged.update(fresh)
      state.user_prefs = merged
      state.staff_role = fetch_my_staff_role()
      state["_prefs_loaded_at"] = time.time()
    elif "user_prefs" not in state:
      # ბაზა არ პასუხობს: დაბლოკვა (fail-closed), მაგრამ გასაგები შეტყობინებით
      return Account(dict(DEFAULT_PREFS), SubscriptionState(False, "inactive"), None, load_failed=True)

  prefs = state.user_prefs
  return Account(prefs, evaluate(prefs), state.get("staff_role"))
