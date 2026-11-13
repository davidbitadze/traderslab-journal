"""ადმინის პანელის ბაზასთან მუშაობა. ყველა ოპერაცია ბაზის ფუნქციებზე გადის, რომლებიც
თავად ამოწმებენ ადმინის უფლებას (is_admin), ამიტომ ეს ფაილი ვერაფერს დაუშვებს ისეთს,
რასაც ბაზა არ დაუშვებდა."""

import pandas as pd

from database import call_rpc

ERROR_TEXTS = {
    "not_admin": "ადმინისტრატორის უფლება არ გაქვთ.",
    "would_go_negative": "ბალანსი მინუსში ვერ გავა.",
    "user_not_found": "მომხმარებელი ვერ მოიძებნა.",
    "invalid_amount": "რაოდენობა არასწორია.",
    "invalid_status": "სტატუსი არასწორია.",
    "invalid_email": "ელ-ფოსტა არასწორია.",
    "invalid_role": "როლი არასწორია.",
    "cannot_demote_self": "საკუთარ თავს ადმინის როლს ვერ ჩამოართმევთ.",
    "cannot_remove_self": "საკუთარ თავს ვერ ამოშლით.",
    "not_found": "ჩანაწერი ვერ მოიძებნა.",
}


def _explain(error):
  text = str(error or "")
  for code, message in ERROR_TEXTS.items():
    if code in text:
      return message
  return text or "უცნობი შეცდომა"


def _action(name, params):
  """RPC, რომელიც {"ok": bool, "error": code} აბრუნებს -> (ok, error_text, data)."""
  data, error = call_rpc(name, params)
  if error:
    return False, _explain(error), None
  if isinstance(data, dict) and not data.get("ok", True):
    return False, _explain(data.get("error")), data
  return True, None, data


def _frame(name, params=None):
  data, error = call_rpc(name, params)
  if error:
    return pd.DataFrame(), _explain(error)
  return pd.DataFrame(data or []), None


def list_users():
  return _frame("admin_list_users")


def adjust_credits(user_id, delta, reason):
  return _action("admin_adjust_credits", {"p_user": user_id, "p_delta": float(delta), "p_reason": reason or None})


def set_subscription(user_id, status, expires_at_iso=None, clear_expiry=False):
  return _action(
      "admin_set_subscription",
      {"p_user": user_id, "p_status": status, "p_expires": expires_at_iso, "p_clear_expiry": bool(clear_expiry)},
  )


def credit_history(user_id, limit=30):
  return _frame("admin_credit_history", {"p_user": user_id, "p_limit": limit})


def list_staff():
  return _frame("admin_list_staff")


def set_staff(email, role):
  return _action("admin_set_staff", {"p_email": email, "p_role": role})


def remove_staff(email):
  return _action("admin_remove_staff", {"p_email": email})


def audit_log(limit=50):
  return _frame("admin_audit_list", {"p_limit": limit})
