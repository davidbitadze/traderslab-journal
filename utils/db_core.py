import streamlit as str_lit
from supabase import create_client


def _make_client(auth_safe=False):
  url, key = str_lit.secrets["SUPABASE_URL"], str_lit.secrets["SUPABASE_KEY"]
  if auth_safe:
    try:
      from supabase import ClientOptions

      return create_client(
          url,
          key,
          options=ClientOptions(auto_refresh_token=False, persist_session=False),
      )
    except Exception:
      pass
  return create_client(url, key)


def new_auth_client():
  """ერთი მომხმარებლის სესიისთვის ახალი კლიენტი. login-ის შემდეგ მასზე ინახება მისი JWT."""
  return _make_client(auth_safe=True)


get_supabase_client = new_auth_client


@str_lit.cache_resource
def _anon_client():
  return _make_client()


def get_data_client():
  """მონაცემებისთვის: ავტორიზებული მომხმარებლის საკუთარი კლიენტი ან უფლებებმოკლებული anon კლიენტი."""
  return str_lit.session_state.get("sb") or _anon_client()


def _uid():
  """ქეშის გასაღებში ვრთავთ user_id-ს, რომ ერთი მომხმარებლის მონაცემი სხვას არ დაუბრუნდეს."""
  user = str_lit.session_state.get("user")
  return getattr(user, "id", None)
