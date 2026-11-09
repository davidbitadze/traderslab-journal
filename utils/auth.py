"""ავტორიზაცია: Supabase-ის რეალური სესია + "მიმახსოვრე" cookie.

როგორ მუშაობს:
* login-ზე იქმნება ამ მომხმარებლის საკუთარი Supabase კლიენტი (st.session_state["sb"]),
  რომელსაც მისი JWT უჭირავს. ბაზა მას ამ JWT-ით ცნობს (RLS).
* "მიმახსოვრე" მონიშნულია -> ბრაუზერის cookie-ში ინახება მხოლოდ Supabase-ის refresh token.
  მასში არც პაროლია, არც uid/email. რეფრეშისას სერვერი cookie-ს კითხულობს და Supabase-ისგან
  ამოწმებს. გაყალბებული ან გაუქმებული token უბრალოდ არ მუშაობს.
* გასვლისას სესია Supabase-შიც უქმდება და cookie იშლება.
"""

import json
import re
import time

import streamlit as st
import streamlit.components.v1 as components

from database import new_auth_client

COOKIE_NAME = "tl_rt"
COOKIE_DAYS = 30
REFRESH_MARGIN = 120  # წამი: access token-ს ვანახლებთ ვადის გასვლამდე ამდენით ადრე
_TOKEN_RE = re.compile(r"^[A-Za-z0-9._\-]{6,512}$")


# ------------------------------------------------------------------ cookie
def _queue_cookie(action, token=None):
  st.session_state["_cookie_cmd"] = (action, token)


def flush_cookie_cmd():
  """app.py-ში ყოველი გაშვების დასაწყისში იძახება: რიგში მდგომარე cookie-ს ბრძანებას
  ბრაუზერში ასრულებს (ერთხელ). ჩაწერა ხდება JS-ით, ამიტომ HttpOnly ვერ იქნება:
  ამის გამო მომხმარებლის ტექსტი HTML-ში ყოველთვის escape-ით ჩავსვათ."""
  cmd = st.session_state.pop("_cookie_cmd", None)
  if not cmd:
    return
  action, token = cmd
  if action == "set" and token and _TOKEN_RE.match(token):
    max_age = COOKIE_DAYS * 24 * 3600
    value = json.dumps(token)
    script = f"""
      const d = window.parent.document;
      const secure = window.parent.location.protocol === 'https:' ? '; Secure' : '';
      d.cookie = '{COOKIE_NAME}=' + {value} + '; path=/; max-age={max_age}; SameSite=Lax' + secure;
    """
  else:
    script = f"""
      const d = window.parent.document;
      d.cookie = '{COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax';
    """
  components.html(f"<script>try {{ {script} }} catch (e) {{}}</script>", height=0)


# ----------------------------------------------------------------- session
def _adopt(client, session, remember):
  st.session_state["sb"] = client
  st.session_state["user"] = session.user
  st.session_state["_remember"] = bool(remember)
  st.session_state.pop("_logged_out", None)
  if remember and session.refresh_token:
    _queue_cookie("set", session.refresh_token)
  else:
    _queue_cookie("clear")


def login(email, password, remember):
  """აბრუნებს (True, None) ან (False, შეცდომის ტექსტი)."""
  try:
    client = new_auth_client()
    response = client.auth.sign_in_with_password(
        {"email": email.strip(), "password": password}
    )
    if response.user and response.session:
      _adopt(client, response.session, remember)
      return True, None
    return False, "ელ-ფოსტა ან პაროლი არასწორია"
  except Exception as e:
    return False, str(e)


def restore_session():
  """გვერდის რეფრეშისას cookie-დან სესიის აღდგენა. სესიაზე მაქსიმუმ ერთხელ ვცდილობთ."""
  if st.session_state.get("user") is not None:
    return
  if st.session_state.get("_logged_out") or st.session_state.get("_restore_tried"):
    return
  st.session_state["_restore_tried"] = True

  dbg = st.session_state.setdefault("_auth_dbg", {})
  try:
    cookies = st.context.cookies
    dbg["server_cookie_names"] = sorted(cookies.keys())
    token = cookies.get(COOKIE_NAME)
  except Exception as e:
    token = None
    dbg["cookie_read_error"] = repr(e)
  dbg["token_found"] = bool(token)
  if not token or not _TOKEN_RE.match(token):
    return

  try:
    client = new_auth_client()
    response = client.auth.refresh_session(token)
    if response and response.session and response.user:
      _adopt(client, response.session, remember=True)  # ახალი (rotated) token cookie-ში ჩაიწერება
      dbg["restore"] = "ok"
      return
    dbg["restore"] = "no session returned"
  except Exception as e:
    dbg["restore"] = f"error: {e}"
  _queue_cookie("clear")  # ცუდი ან ვადაგასული token: ვასუფთავებთ


def ensure_fresh_session():
  """access token მალე თუ იწურება, ვანახლებთ. თუ ვერ განახლდა, მომხმარებელი გამოდის."""
  client = st.session_state.get("sb")
  if client is None:
    return
  try:
    session = client.auth.get_session()
    expires_at = getattr(session, "expires_at", None) if session else None
    if session is None:
      raise RuntimeError("no session")
    if expires_at and expires_at - time.time() > REFRESH_MARGIN:
      return
    response = client.auth.refresh_session()
    if not (response and response.session):
      raise RuntimeError("refresh failed")
    st.session_state["user"] = response.session.user
    if st.session_state.get("_remember"):
      _queue_cookie("set", response.session.refresh_token)
  except Exception:
    logout(rerun=True, revoke=False)


def logout(rerun=True, revoke=True):
  client = st.session_state.get("sb")
  if client is not None and revoke:
    try:
      client.auth.sign_out()
    except Exception:
      pass
  for key in ("sb", "user", "user_prefs", "_credits_cache", "_remember"):
    st.session_state.pop(key, None)
  st.session_state["_logged_out"] = True
  _queue_cookie("clear")
  if rerun:
    st.rerun()


def register(email, password):
  """აბრუნებს (True, None) ან (False, შეცდომა). სესიას არ ქმნის: ჯერ მეილი უნდა დადასტურდეს."""
  try:
    response = new_auth_client().auth.sign_up(
        {"email": email.strip(), "password": password}
    )
    return bool(response.user), None
  except Exception as e:
    return False, str(e)


def render_debug():
  """დიაგნოსტიკა (მხოლოდ ბმულზე ?debug=1): cookie-ს მხოლოდ სახელებს აჩვენებს, მნიშვნელობებს არა."""
  with st.expander("🛠 auth debug", expanded=True):
    st.write(
        {
            "streamlit": st.__version__,
            "logged_in": st.session_state.get("user") is not None,
            "logged_out_flag": bool(st.session_state.get("_logged_out")),
            "pending_cookie_cmd": (st.session_state.get("_cookie_cmd") or [None])[0],
            **st.session_state.get("_auth_dbg", {}),
        }
    )
    components.html(
        """<div id=o style="font:12px monospace;color:#888">...</div>
        <script>try{const n=window.parent.document.cookie.split(';').map(c=>c.split('=')[0].trim()).filter(Boolean);
        document.getElementById('o').textContent='browser cookie names: '+JSON.stringify(n);}
        catch(e){document.getElementById('o').textContent='browser cookie read failed: '+e;}</script>""",
        height=40,
    )
