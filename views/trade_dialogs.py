import html
from datetime import datetime
import os
import uuid
import pandas as pd
import streamlit as st
from i18n import t
from database import (
    delete_trade,
    fetch_trades,
    insert_trade,
    update_trade,
    upload_screenshot,
    delete_screenshot,
    fetch_settings,
)
from utils.ai_mentor import ai_status, calculate_cost, generate_trade_analysis, get_extra_costs
from utils.credits import (
    charge_credits,
    check_has_enough_credits,
    get_user_credits_cached,
    refund_charge,
)
from utils.dates import (
    format_db_datetime,
    format_display_datetime,
    parse_date_series,
    parse_trade_datetime,
)
from utils.formulas import calculate_net_pnl, pnl_breakdown, to_float

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"
ORANGE = "#f97316"

START_ROW_MARK = "Start Row"
SUB_ACTION_TYPES = [
    "ნაწილობრივი დახურვა",
    "სრული დახურვა",
    "დამატებითი შესვლა",
    "ცვლილება",
]
EDIT_STATE_KEY = "edit_sub_id"

# ბაზაში ეტაპის ტიპი ქართული კოდით ინახება (ფორმულები მასზეა მიბმული), ეკრანზე ენის მიხედვით ითარგმნება
_ACTION_KEYS = {
    "ნაწილობრივი დახურვა": "act_partial_close",
    "სრული დახურვა": "act_full_close",
    "დამატებითი შესვლა": "act_add_entry",
    "ცვლილება": "act_modify",
}


def _lang():
  return st.session_state.get("lang", "ka")


def _tt(key, **fmt):
  return t(key, _lang(), **fmt)


def _action_label(value):
  """ეტაპის ტიპი ეკრანისთვის (ბაზაში შენახული მნიშვნელობა არ იცვლება)."""
  text = str(value)
  if START_ROW_MARK in text:
    return _tt("act_start_row")
  key = _ACTION_KEYS.get(text.strip())
  return _tt(key) if key else text

def _has_value(value):
  return value is not None and str(value).strip() not in (
      "", "None", "nan", "NaT", "<NA>", "No Screenshot",
  )

def _txt(value):
  return str(value).strip() if _has_value(value) else ""

def _parse_num(text):
  try:
    return float(str(text).strip().replace(",", "."))
  except (ValueError, TypeError):
    return None

def _get_image_url(val):
  if not _has_value(val):
    return None
  val_str = str(val).strip()
  if val_str.startswith("http://") or val_str.startswith("https://"):
    return val_str
  supabase_url = st.secrets.get("SUPABASE_URL", "")
  if supabase_url:
    return f"{supabase_url}/storage/v1/object/public/screenshots/{val_str}"
  return None

def _pretty_date(value):
  return format_display_datetime(value)

def _sort_by_date(frame):
  date_col = None
  for candidate in ["Date", "date", "Entry Date", "entry_date"]:
    if candidate in frame.columns and frame[candidate].notna().any():
      date_col = candidate
      break
  if date_col is None or frame.empty:
    return frame, date_col
  order = parse_date_series(frame[date_col])
  ordered = frame.assign(_order=order).sort_values("_order", kind="stable")
  return ordered.drop(columns="_order"), date_col

def recalc_net_pnl(parent_id, clear_if_none=True):
  df = fetch_trades()
  if df.empty:
    return
  main_df = df[df["Trade ID"] == parent_id]
  if main_df.empty:
    return
  subs = df[df["Parent Trade ID"] == parent_id]
  net = calculate_net_pnl(main_df.iloc[0], subs)
  if net is None and not clear_if_none:
    return
  update_trade(parent_id, {"Net P/L": None if net is None else str(net)})

def _close_edit_screen():
  st.session_state.pop(EDIT_STATE_KEY, None)
  st.rerun(scope="fragment")

def _run_ai_analysis(trade, sub_actions, trade_id, user_id, mode, cost, opt_detailed, opt_advice):
  if not user_id:
    st.error(_tt("err_auth"))
    return

  charge = None
  if cost > 0:
    if not check_has_enough_credits(user_id, cost):
      st.error(_tt("err_not_enough_credits", cost=cost))
      return
    charge = charge_credits(user_id, cost, f"ai_analysis:{trade_id}")
    if not charge.ok:
      st.error(f"❌ {charge.error}")
      return

  lang = st.session_state.get("lang", "ka")
  with st.spinner(_tt("ai_running")):
    result = generate_trade_analysis(trade, sub_actions, opt_detailed, opt_advice, lang)

  saved = False
  if result.ok:
    saved = update_trade(trade_id, {"ai_analysis": result.analysis, "ai_scores": result.scores})

  if not (result.ok and saved):
    refunded = refund_charge(user_id, charge) if charge else True
    reason = result.error or _tt("ai_save_failed")
    suffix = _tt("ai_refunded") if charge and refunded else ""
    st.error(f"❌ {reason}{suffix}")
    return

  trade["ai_analysis"] = result.analysis
  trade["ai_scores"] = result.scores
  st.success(_tt("ai_done"))
  st.rerun(scope="fragment")

_NUM_NAMES = {
    "ფასი": lambda: _tt("n_price"),
    "მოცულობა": lambda: _tt("n_qty"),
    "რისკი": lambda: _tt("n_risk"),
}


def _render_sub_edit(trade_id, sub, date_col):
  sub_id = sub.get("Trade ID")
  sub_type = _txt(sub.get("ActionType"))
  is_start = START_ROW_MARK in sub_type
  date_col = date_col or "Entry Date"
  orig_date = _txt(sub.get(date_col))
  parsed_orig = parse_trade_datetime(orig_date)
  shown_date = format_db_datetime(parsed_orig) if not pd.isna(parsed_orig) else orig_date
  current_img = _get_image_url(sub.get("Screenshot"))

  st.markdown(_tt("stage_edit_title"))
  st.caption(f"{sub.get('Pair', '')} · {_action_label(sub_type)}")

  user_patterns = fetch_settings("pattern")
  user_triggers = fetch_settings("trigger")

  orig_pattern = _txt(sub.get("Pattern"))
  orig_trigger = _txt(sub.get("Trigger"))
  orig_side = _txt(sub.get("Side")) or "Long"

  with st.form(key=f"form_edit_sub_{sub_id}"):
    if is_start:
      new_type = sub_type
    else:
      options = list(SUB_ACTION_TYPES)
      if sub_type and sub_type not in options:
        options.insert(0, sub_type)
      new_type = st.selectbox(_tt("f_action"), options, index=options.index(sub_type) if sub_type in options else 0, format_func=_action_label)

    # ზოლი 1
    st.markdown("---")
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    date_txt = r1_c1.text_input(_tt("f_datetime"), value=shown_date, placeholder="YYYY-MM-DD HH:MM:SS")
    price_txt = r1_c2.text_input(_tt("f_entry_price"), value=_txt(sub.get("Entry Price")))
    qty_txt = r1_c3.text_input(_tt("f_qty"), value=_txt(sub.get("Qty")))

    # ზოლი 2
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    sl_txt = r2_c1.text_input(_tt("f_sl"), value=_txt(sub.get("SL_Price")))
    tp_txt = r2_c2.text_input(_tt("f_tp"), value=_txt(sub.get("TP_Price")))
    risk_txt = r2_c3.text_input(_tt("f_risk"), value=_txt(sub.get("Risk ($)")))

    # ზოლი 3
    orig_desc = _txt(sub.get("Description"))
    desc_txt = st.text_area(_tt("f_description"), value=orig_desc, key=f"edit_sub_desc_{sub_id}")

    img_col, upload_col = st.columns([1, 2], vertical_alignment="center")
    with img_col:
      if current_img:
        st.image(current_img, caption=_tt("current_screenshot"), width=180)
      else:
        st.caption(_tt("no_screenshot"))
    with upload_col:
      new_file = st.file_uploader(_tt("replace_screenshot"), type=["png", "jpg", "jpeg"], key=f"edit_sub_img_{sub_id}")

    # ზოლი 4
    r4_c1, r4_c2, r4_c3 = st.columns(3)
    p_opts = user_patterns if user_patterns else list(t("default_patterns", lang))
    if orig_pattern and orig_pattern not in p_opts:
      p_opts.insert(0, orig_pattern)
    selected_pattern = r4_c1.selectbox(_tt("f_pattern"), p_opts, index=p_opts.index(orig_pattern) if orig_pattern in p_opts else 0, key=f"edit_pattern_{sub_id}")

    t_opts = user_triggers if user_triggers else list(t("default_triggers", lang))
    if orig_trigger and orig_trigger not in t_opts:
      t_opts.insert(0, orig_trigger)
    selected_trigger = r4_c2.selectbox(_tt("f_trigger"), t_opts, index=t_opts.index(orig_trigger) if orig_trigger in t_opts else 0, key=f"edit_trigger_{sub_id}")

    side_opts = ["Long", "Short"]
    if orig_side.capitalize() not in side_opts:
      side_opts.insert(0, orig_side)
    selected_side = r4_c3.selectbox(_tt("f_side"), side_opts, index=side_opts.index(orig_side.capitalize()) if orig_side.capitalize() in side_opts else 0, key=f"edit_side_{sub_id}")

    st.markdown("---")
    b1, b2 = st.columns(2)
    save = b1.form_submit_button(_tt("save_btn"), type="primary", use_container_width=True)
    cancel = b2.form_submit_button(_tt("cancel"), use_container_width=True)

  if cancel:
    _close_edit_screen()

  if save:
    # ფასი და მოცულობა სავალდებულოა; რისკი მხოლოდ საწყის სტრიქონში (ნაწილობრივ/სრულ დახურვას რისკი არ სჭირდება)
    required = {"ფასი": price_txt, "მოცულობა": qty_txt}  # გასაღებები შიდაა; ეკრანზე _NUM_NAMES-ით ითარგმნება
    if is_start or risk_txt.strip():
      required["რისკი"] = risk_txt
    parsed = {name: _parse_num(text) for name, text in required.items()}
    parsed.setdefault("რისკი", 0.0)
    errors = [_tt("err_invalid_number", name=_NUM_NAMES[n]()) for n, v in parsed.items() if v is None]

    optional = {}
    for name, text in (("SL", sl_txt), ("TP", tp_txt)):
      if not text.strip():
        optional[name] = 0.0
      else:
        value = _parse_num(text)
        if value is None:
          errors.append(_tt("err_invalid_number", name=name))
        else:
          optional[name] = value

    new_date = None
    if date_txt.strip() != orig_date:
      parsed_date = parse_trade_datetime(date_txt)
      if pd.isna(parsed_date):
        errors.append(_tt("err_date_unreadable"))
      else:
        new_date = format_db_datetime(parsed_date)

    if errors:
      for message in errors:
        st.error(message)
    else:
      payload = {
          "Entry Price": str(parsed["ფასი"]),
          "Qty": str(parsed["მოცულობა"]),
          "Description": desc_txt,
          "Risk ($)": str(parsed["რისკი"]),
          "SL_Price": str(optional["SL"]),
          "TP_Price": str(optional["TP"]),
          "Pattern": selected_pattern,
          "Trigger": selected_trigger,
          "Side": selected_side,
      }
      if not is_start:
        payload["ActionType"] = new_type
      if new_date is not None:
        payload[date_col] = new_date
      if new_file is not None:
        ext = os.path.splitext(new_file.name)[1].lower() or ".png"
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_name = f"sub_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
        uploaded_url = upload_screenshot(new_file, file_name=safe_name)
        if uploaded_url:
          payload["Screenshot"] = uploaded_url

      if update_trade(sub_id, payload):
        if new_file is not None and uploaded_url and current_img:
          delete_screenshot(current_img)
        recalc_net_pnl(trade_id)
        st.toast(_tt("toast_stage_updated"), icon="✅")
        _close_edit_screen()

  if not is_start:
    st.divider()
    confirm = st.checkbox(_tt("confirm_delete_stage"), key=f"confirm_del_sub_{sub_id}")
    if st.button(_tt("delete_stage_btn"), key=f"del_sub_{sub_id}", disabled=not confirm, use_container_width=True):
      if delete_trade(sub_id):
        recalc_net_pnl(trade_id)
        st.toast(_tt("toast_stage_deleted"), icon="🗑️")
        _close_edit_screen()


@st.dialog("🔍", width="large")  # სათაური ენაზე დამოუკიდებელია; ტექსტური სათაური ფანჯრის შიგნითაა
def show_trade_details_dialog(trade, df=None):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

  df = fetch_trades()
  fresh = df[df["Trade ID"] == trade_id]
  if not fresh.empty:
    trade = fresh.iloc[0].to_dict()

  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  main_screenshot = trade.get("Screenshot")
  sub_actions, date_col = _sort_by_date(df[df["Parent Trade ID"] == trade_id])

  edit_id = st.session_state.get(EDIT_STATE_KEY)
  if edit_id:
    match = sub_actions[sub_actions["Trade ID"] == edit_id]
    if not match.empty:
      _render_sub_edit(trade_id, match.iloc[0], date_col)
      return
    st.session_state.pop(EDIT_STATE_KEY, None)

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  st.markdown(f"##### {_tt('dialog_title')}")
  st.markdown(f"### {pair} — **{side}**")

  col_st1, col_st2, col_st3 = st.columns([3, 3, 2], vertical_alignment="center")
  with col_st1:
    new_status = st.toggle(_tt("status_finalized") if is_finalized else _tt("status_ongoing"), value=is_finalized, key=f"dialog_toggle_fin_{trade_id}")
    if new_status != is_finalized:
      update_trade(trade_id, {"Finalized": str(new_status)})
      recalc_net_pnl(trade_id, clear_if_none=False)
      st.toast(_tt("toast_status_updated"), icon="🔄")
      st.rerun()  # მთლიანი გვერდი: ჟურნალის სია (მიმდინარე/დასრულებული) ახალ სტატუსს მაშინვე აჩვენებს

  with col_st2:
    status_badge = "🏁 " + _tt("status_finalized") if is_finalized else "⚡ " + _tt("status_ongoing")
    badge_color = GRAY if is_finalized else ORANGE
    st.markdown(f"{html.escape(_tt('status_label'))}: <b style='color:{badge_color}'>{html.escape(status_badge)}</b>", unsafe_allow_html=True)

  with col_st3:
    if st.button(_tt("delete_trade_btn"), key=f"dlg_del_{trade_id}", use_container_width=True):
      if delete_trade(trade_id):
        st.success(_tt("trade_deleted"))
        st.rerun()

  st.divider()

  img_url = _get_image_url(main_screenshot)
  if img_url:
    st.image(img_url, use_container_width=True)
  else:
    st.warning(_tt("warn_missing_screenshot"))

  st.divider()

  st.markdown(_tt("manage_header"))

  if not sub_actions.empty:
    sub_items = list(sub_actions.iterrows())
    for i in range(0, len(sub_items), 3):
      chunk = sub_items[i : i + 3]
      cols = st.columns(3, vertical_alignment="top")
      for j, (row_idx, row) in enumerate(chunk):
        sub_id = row.get("Trade ID") or row.get("id") or row_idx
        sub_type = "Action"
        for k in ["ActionType", "Action Type", "action_type", "Action"]:
          val = row.get(k)
          if _has_value(val):
            sub_type = val
            break

        sub_price = 0.0
        for k in ["Price", "price", "Entry Price", "entry_price"]:
          val = row.get(k)
          if _has_value(val):
            sub_price = val
            break

        sub_qty = 0.0
        for k in ["Quantity", "quantity", "Qty", "qty"]:
          val = row.get(k)
          if _has_value(val):
            sub_qty = val
            break

        sub_date = row.get(date_col, "") if date_col else ""
        sub_img = None
        for k in ["Screenshot", "screenshot"]:
          val = row.get(k)
          if _has_value(val):
            sub_img = _get_image_url(val)
            break

        with cols[j]:
          with st.container(border=True):
            c_img, c_desc = st.columns([1, 2], vertical_alignment="center")
            with c_img:
              if sub_img:
                st.markdown(f"<img src='{html.escape(str(sub_img), quote=True)}' class='sub-action-img' loading='lazy'>", unsafe_allow_html=True)
              else:
                st.markdown("<div class='sub-action-placeholder'>📁</div>", unsafe_allow_html=True)
            with c_desc:
              st.markdown(f"**{_action_label(sub_type)}**")
              st.markdown(f"{_tt('label_price')}: `{sub_price}`")
              st.markdown(f"{_tt('label_volume')}: `{sub_qty}`")
              st.caption(f"📅 {_pretty_date(sub_date) if _has_value(sub_date) else ''}")

            if st.button(_tt("edit_btn"), key=f"btn_edit_sub_{sub_id}", use_container_width=True):
              st.session_state[EDIT_STATE_KEY] = sub_id
              st.rerun(scope="fragment")
  else:
    st.info(_tt("no_sub_actions"))

  with st.expander(_tt("add_action_expander")):
    with st.form(key=f"form_add_sub_{trade_id}", clear_on_submit=True):
      add_date = st.text_input(_tt("f_datetime"), value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key=f"add_sub_date_{trade_id}")
      add_type = st.selectbox(_tt("f_action_type"), SUB_ACTION_TYPES, format_func=_action_label)
      a1, a2 = st.columns(2)
      add_price = a1.number_input(_tt("f_price"), value=0.0, format="%.5f")
      add_qty = a2.number_input(_tt("f_qty_short"), value=1.0, format="%.2f")
      add_description = st.text_area(_tt("f_description"), value="", key=f"add_sub_desc_{trade_id}")
      add_file = st.file_uploader(_tt("f_mid_screenshot"), type=["png", "jpg", "jpeg"], key=f"sub_img_up_{trade_id}")
      add_submit = st.form_submit_button(_tt("add_data_btn"), use_container_width=True)

    if add_submit:
      parsed_add_date = parse_trade_datetime(add_date)
      if pd.isna(parsed_add_date):
        st.error(_tt("err_date_unreadable"))
      else:
        sub_screenshot_url = ""
        if add_file is not None:
          ext = os.path.splitext(add_file.name)[1].lower() or ".png"
          stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
          safe_name = f"sub_{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
          sub_screenshot_url = upload_screenshot(add_file, file_name=safe_name) or ""

        sub_payload = {
            "Trade ID": str(uuid.uuid4()),
            "Parent Trade ID": trade_id,
            "Entry Date": format_db_datetime(parsed_add_date),
            "Pair": pair,
            "Side": side,
            "ActionType": add_type,
            "Entry Price": str(add_price),
            "Qty": str(add_qty),
            "Description": add_description,
            "Screenshot": sub_screenshot_url,
            "Finalized": "False",
        }
        if insert_trade(sub_payload):
          recalc_net_pnl(trade_id, clear_if_none=False)
          st.toast(_tt("toast_added"), icon="✅")
          st.rerun(scope="fragment")

  st.divider()
  st.markdown(_tt("ai_header"))
  user_id = st.session_state.user.id if st.session_state.user else None
  mode = ai_status()

  if mode == "disabled":
    st.info(_tt("ai_disabled"))
  else:
    current_credits = get_user_credits_cached(user_id) if user_id else 0.0
    st.caption(_tt("ai_balance", credits=current_credits))
    if mode == "demo":
      st.caption(_tt("ai_demo"))

    det_cost, adv_cost = get_extra_costs()
    opt_detailed = st.toggle(
        f"{_tt('ai_opt_detailed')} (+{det_cost:g})", key=f"ai_opt_det_{trade_id}"
    )
    opt_advice = st.toggle(
        f"{_tt('ai_opt_advice')} (+{adv_cost:g})", key=f"ai_opt_adv_{trade_id}"
    )
    total_cost = calculate_cost(opt_detailed, opt_advice)
    if st.button(_tt("ai_send", cost=total_cost), key=f"ai_send_{trade_id}", use_container_width=True):
      _run_ai_analysis(trade, sub_actions, trade_id, user_id, mode, total_cost, opt_detailed, opt_advice)

  stored_analysis = trade.get("ai_analysis")
  if _has_value(stored_analysis):
    with st.expander(_tt("ai_result"), expanded=True):
      st.markdown(stored_analysis)

  st.divider()
  breakdown = pnl_breakdown(trade, sub_actions)
  st.markdown(_tt("pnl_calc_header"))
  if breakdown is None:
    st.caption(_tt("no_exit_yet"))
  else:
    lines = [_tt("pnl_entry_line", p=breakdown["entry_avg"], q=breakdown["entry_qty"])]
    if breakdown["exit_avg"] is not None:
      lines.append(_tt("pnl_exit_line", p=breakdown["exit_avg"], q=breakdown["exit_qty"]))
    lines.append(_tt("pnl_risk_line", risk=breakdown["risk"], pnl=breakdown["pnl"]))
    st.markdown("\n".join(lines))

  st.divider()
  if st.button(_tt("close_btn"), key=f"close_dlg_{trade_id}", use_container_width=True):
    st.rerun()
