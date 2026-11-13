from datetime import datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st

from utils import admin_api
from utils.subscription import ALL_STATUSES, evaluate, parse_expiry

QUICK_CREDITS = (10, 50, 100)
QUICK_DAYS = (30, 90, 365)
EXPIRING_SOON_DAYS = 7


def _tx(lang, ka, en):
  return ka if lang == "ka" else en


def _fmt_dt(value):
  try:
    moment = parse_expiry(value)
  except (ValueError, TypeError, OverflowError):
    return str(value)
  return moment.strftime("%Y-%m-%d %H:%M") if moment else "—"


def _state_of(row, now):
  """მომხმარებლის მდგომარეობა ცხრილისთვის: ok | expiring | expired | inactive | none."""
  if pd.isna(row.get("subscription_status")):
    return "none"  # ანგარიში არსებობს, პარამეტრების რიგი ჯერ არ შექმნილა
  prefs = {
      "subscription_status": row.get("subscription_status"),
      "subscription_expires_at": None if pd.isna(row.get("subscription_expires_at")) else row.get("subscription_expires_at"),
  }
  state = evaluate(prefs, now)
  if state.valid:
    return "expiring" if state.days_left is not None and state.days_left <= EXPIRING_SOON_DAYS else "ok"
  return "expired" if state.reason == "expired" else "inactive"


def _result(ok, error, success_text):
  """ოპერაციის შედეგის ჩვენება; წარმატებისას ეკრანს ანახლებს."""
  if ok:
    st.toast(success_text, icon="✅")
    st.rerun()
  else:
    st.error(f"❌ {error}")


# ------------------------------------------------------------------ users tab
def _render_users(lang, now):
  df, error = admin_api.list_users()
  if error:
    st.error(f"❌ {error}")
    return
  if df.empty:
    st.info(_tx(lang, "მომხმარებლების ჩანაწერები ჯერ არ არის.", "No users yet."))
    return

  df["state"] = df.apply(lambda r: _state_of(r, now), axis=1)
  labels = {
      "ok": _tx(lang, "🟢 აქტიური", "🟢 Active"),
      "expiring": _tx(lang, "🟠 მალე ამოიწურება", "🟠 Expiring soon"),
      "expired": _tx(lang, "🔴 ვადაგასული", "🔴 Expired"),
      "inactive": _tx(lang, "⛔ გამორთული", "⛔ Inactive"),
      "none": _tx(lang, "⚪ პარამეტრების გარეშე", "⚪ No preferences"),
  }

  total_credits = pd.to_numeric(df["credits_balance"], errors="coerce").fillna(0).sum()
  metrics = st.columns(5)
  metrics[0].metric(_tx(lang, "მომხმარებელი", "Users"), len(df))
  metrics[1].metric(_tx(lang, "აქტიური", "Active"), int(df["state"].isin(["ok", "expiring"]).sum()))
  metrics[2].metric(_tx(lang, "მალე ამოიწურება", "Expiring soon"), int((df["state"] == "expiring").sum()))
  metrics[3].metric(_tx(lang, "ვადაგასული/გამორთული", "Expired/inactive"), int(df["state"].isin(["expired", "inactive"]).sum()))
  metrics[4].metric(_tx(lang, "ქულები ჯამში", "Credits total"), f"{total_credits:g}")

  f1, f2 = st.columns([2, 2])
  query = f1.text_input(_tx(lang, "🔎 ძებნა ელ-ფოსტით", "🔎 Search by e-mail"), key="admin_search").strip().lower()
  chosen = f2.multiselect(
      _tx(lang, "ფილტრი მდგომარეობით", "Filter by state"),
      options=list(labels),
      format_func=lambda k: labels[k],
      key="admin_state_filter",
  )

  view = df
  if query:
    view = view[view["email"].fillna("").str.lower().str.contains(query, regex=False)]
  if chosen:
    view = view[view["state"].isin(chosen)]

  table = pd.DataFrame({
      _tx(lang, "ელ-ფოსტა", "E-mail"): view["email"],
      _tx(lang, "მდგომარეობა", "State"): view["state"].map(labels),
      _tx(lang, "ქულა", "Credits"): pd.to_numeric(view["credits_balance"], errors="coerce"),
      _tx(lang, "ვადა (UTC)", "Expires (UTC)"): view["subscription_expires_at"].map(lambda v: "—" if pd.isna(v) else _fmt_dt(v)),
      _tx(lang, "გარიგებები", "Trades"): view["trades_count"],
      _tx(lang, "რეგისტრაცია", "Registered"): view["created_at"].map(_fmt_dt),
      _tx(lang, "ბოლო შესვლა", "Last sign-in"): view["last_sign_in_at"].map(lambda v: "—" if pd.isna(v) else _fmt_dt(v)),
  })
  st.dataframe(table, use_container_width=True, hide_index=True)

  if view.empty:
    return

  st.divider()
  options = list(view["user_id"])
  email_of = dict(zip(view["user_id"], view["email"].fillna("?")))
  target = st.selectbox(
      _tx(lang, "აირჩიეთ მომხმარებელი სამართავად", "Select a user to manage"),
      options=options,
      format_func=lambda uid: email_of.get(uid, uid),
      key="admin_user_select",
  )
  row = df[df["user_id"] == target].iloc[0]
  _render_user_panel(lang, now, row)


def _render_user_panel(lang, now, row):
  user_id = row["user_id"]
  has_prefs = not pd.isna(row.get("subscription_status"))
  if not has_prefs:
    st.warning(_tx(
        lang,
        "ამ მომხმარებელს პარამეტრების რიგი ჯერ არ აქვს (აპში არ შესულა). შესვლისას ავტომატურად შეიქმნება.",
        "This user has no preferences row yet (never opened the app). It is created on first sign-in.",
    ))
    return

  balance = float(row["credits_balance"] or 0)
  col_credits, col_sub = st.columns(2)

  # ---- credits
  with col_credits:
    with st.container(border=True):
      st.markdown(f"#### 💳 {_tx(lang, 'ქულები', 'Credits')}: **{balance:g}**")
      quick = st.columns(len(QUICK_CREDITS))
      for col, amount in zip(quick, QUICK_CREDITS):
        if col.button(f"+{amount}", key=f"admin_quick_{amount}", use_container_width=True):
          ok, error, _ = admin_api.adjust_credits(user_id, amount, "quick top-up")
          _result(ok, error, _tx(lang, f"დაემატა {amount} ქულა", f"Added {amount} credits"))

      amount = st.number_input(_tx(lang, "რაოდენობა", "Amount"), min_value=0.0, value=10.0, step=5.0, key="admin_amount")
      reason = st.text_input(_tx(lang, "მიზეზი (არასავალდებულო)", "Reason (optional)"), key="admin_reason")
      b1, b2 = st.columns(2)
      if b1.button(_tx(lang, "➕ დამატება", "➕ Add"), use_container_width=True, key="admin_add"):
        ok, error, _ = admin_api.adjust_credits(user_id, amount, reason)
        _result(ok, error, _tx(lang, "ბალანსი განახლდა", "Balance updated"))
      if b2.button(_tx(lang, "➖ ჩამოჭრა", "➖ Deduct"), use_container_width=True, key="admin_deduct"):
        ok, error, _ = admin_api.adjust_credits(user_id, -amount, reason)
        _result(ok, error, _tx(lang, "ბალანსი განახლდა", "Balance updated"))

      exact = st.number_input(_tx(lang, "ზუსტი ბალანსი", "Exact balance"), min_value=0.0, value=balance, step=1.0, key=f"admin_exact_{user_id}")
      if st.button(_tx(lang, "✏️ ბალანსის დაყენება", "✏️ Set balance"), use_container_width=True, key="admin_set_exact"):
        delta = round(exact - balance, 2)
        if delta == 0:
          st.info(_tx(lang, "ბალანსი უკვე ასეთია.", "The balance is already that value."))
        else:
          ok, error, _ = admin_api.adjust_credits(user_id, delta, reason or "set exact balance")
          _result(ok, error, _tx(lang, "ბალანსი განახლდა", "Balance updated"))

  # ---- subscription
  with col_sub:
    with st.container(border=True):
      current = parse_expiry(row.get("subscription_expires_at")) if not pd.isna(row.get("subscription_expires_at")) else None
      st.markdown(
          f"#### 🗓️ {_tx(lang, 'გამოწერა', 'Subscription')}: **{row['subscription_status']}**"
          f" · {_tx(lang, 'ვადა', 'until')}: **{_fmt_dt(current) if current else _tx(lang, 'უვადო', 'no expiry')}**"
      )

      st.caption(_tx(lang, "სწრაფი გაგრძელება (აქტიურად აქცევს):", "Quick extend (sets status to active):"))
      quick = st.columns(len(QUICK_DAYS))
      for col, days in zip(quick, QUICK_DAYS):
        if col.button(f"+{days}d", key=f"admin_extend_{days}", use_container_width=True):
          base = max(current, now) if current else now
          new_expiry = (base + timedelta(days=days)).isoformat()
          ok, error, _ = admin_api.set_subscription(user_id, "active", new_expiry)
          _result(ok, error, _tx(lang, "გამოწერა გაგრძელდა", "Subscription extended"))

      status_index = ALL_STATUSES.index(row["subscription_status"]) if row["subscription_status"] in ALL_STATUSES else 0
      status = st.selectbox(_tx(lang, "სტატუსი", "Status"), ALL_STATUSES, index=status_index, key=f"admin_status_{user_id}")
      no_expiry = st.checkbox(_tx(lang, "უვადო", "No expiry"), value=current is None, key=f"admin_noexp_{user_id}")
      expiry_date = st.date_input(
          _tx(lang, "ვადის ბოლო დღე (UTC)", "Last day (UTC)"),
          value=(current or now + timedelta(days=30)).date(),
          disabled=no_expiry,
          key=f"admin_date_{user_id}",
      )
      if st.button(_tx(lang, "💾 გამოწერის შენახვა", "💾 Save subscription"), use_container_width=True, key="admin_save_sub"):
        expires = datetime.combine(expiry_date, time(23, 59, 59), tzinfo=timezone.utc).isoformat()
        ok, error, _ = admin_api.set_subscription(user_id, status, None if no_expiry else expires, clear_expiry=no_expiry)
        _result(ok, error, _tx(lang, "გამოწერა შენახულია", "Subscription saved"))

  with st.expander(_tx(lang, "📜 ქულების ისტორია", "📜 Credit history")):
    history, error = admin_api.credit_history(user_id, 30)
    if error:
      st.error(f"❌ {error}")
    elif history.empty:
      st.caption(_tx(lang, "ჩანაწერები არ არის.", "No entries."))
    else:
      history = history[["created_at", "kind", "delta", "balance_after", "reason", "actor"]].copy()
      history["created_at"] = history["created_at"].map(_fmt_dt)
      st.dataframe(history, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ staff tab
def _render_staff(lang, my_email):
  st.caption(_tx(
      lang,
      "ადმინი სრულად მართავს პანელს. მენტორი ჩანაწერია მომავალი ფუნქციებისთვის და ადმინის უფლებებს არ იღებს.",
      "Admins fully manage this panel. Mentor is a role marker for future features and grants no admin rights.",
  ))
  staff, error = admin_api.list_staff()
  if error:
    st.error(f"❌ {error}")
    return
  st.dataframe(
      staff[["email", "role", "added_by", "created_at"]].assign(created_at=lambda d: d["created_at"].map(_fmt_dt)),
      use_container_width=True,
      hide_index=True,
  )

  with st.form("admin_add_staff", clear_on_submit=True):
    st.markdown(_tx(lang, "#### ➕ დამატება / როლის შეცვლა", "#### ➕ Add / change role"))
    c1, c2 = st.columns([3, 1])
    email = c1.text_input(_tx(lang, "ელ-ფოსტა", "E-mail"), key="admin_staff_email")
    role = c2.selectbox(_tx(lang, "როლი", "Role"), ["mentor", "admin"], key="admin_staff_role")
    if st.form_submit_button(_tx(lang, "შენახვა", "Save"), use_container_width=True):
      ok, error, _ = admin_api.set_staff(email, role)
      _result(ok, error, _tx(lang, "შენახულია", "Saved"))

  removable = [e for e in staff["email"] if e != my_email]
  if removable:
    with st.form("admin_remove_staff"):
      st.markdown(_tx(lang, "#### 🗑️ ამოღება", "#### 🗑️ Remove"))
      target = st.selectbox(_tx(lang, "ელ-ფოსტა", "E-mail"), removable)
      confirm = st.checkbox(_tx(lang, "ვადასტურებ", "I confirm"))
      if st.form_submit_button(_tx(lang, "ამოღება", "Remove"), use_container_width=True):
        if not confirm:
          st.warning(_tx(lang, "მონიშნეთ დადასტურება.", "Tick the confirmation first."))
        else:
          ok, error, _ = admin_api.remove_staff(target)
          _result(ok, error, _tx(lang, "ამოღებულია", "Removed"))


# ------------------------------------------------------------------ audit tab
def _render_audit(lang):
  log, error = admin_api.audit_log(100)
  if error:
    st.error(f"❌ {error}")
  elif log.empty:
    st.caption(_tx(lang, "ჩანაწერები არ არის.", "No entries."))
  else:
    log = log[["created_at", "actor_email", "action", "target", "details"]].copy()
    log["created_at"] = log["created_at"].map(_fmt_dt)
    log["details"] = log["details"].map(lambda d: "" if d is None else str(d))
    st.dataframe(log, use_container_width=True, hide_index=True)


# ----------------------------------------------------------------------- view
def render_admin_view(lang="ka"):
  # ინტერფეისის შემოწმება; რეალურ დაცვას ბაზა უზრუნველყოფს (ყველა ფუნქცია თავად ამოწმებს უფლებას)
  if st.session_state.get("staff_role") != "admin":
    st.error(_tx(lang, "⛔ თქვენ არ გაქვთ ადმინისტრატორის უფლებები.", "⛔ You do not have administrator permissions."))
    return

  my_email = str(getattr(st.session_state.get("user"), "email", "") or "").lower()
  now = datetime.now(timezone.utc)

  st.title(_tx(lang, "🛡️ ადმინისტრატორის პანელი", "🛡️ Administrator panel"))
  st.caption(f"{_tx(lang, 'ავტორიზებული ადმინი', 'Signed in as')}: **{my_email}**")

  tab_users, tab_staff, tab_audit = st.tabs([
      _tx(lang, "👥 მომხმარებლები", "👥 Users"),
      _tx(lang, "🧑‍🏫 ადმინები და მენტორები", "🧑‍🏫 Admins & mentors"),
      _tx(lang, "📜 ქმედებების ჟურნალი", "📜 Audit log"),
  ])
  with tab_users:
    _render_users(lang, now)
  with tab_staff:
    _render_staff(lang, my_email)
  with tab_audit:
    _render_audit(lang)
