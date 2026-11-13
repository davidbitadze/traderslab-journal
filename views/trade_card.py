from datetime import datetime
import html
import os
import uuid
import pandas as pd
import streamlit as st
from database import (
    delete_trade,
    fetch_trades,
    insert_trade,
    update_trade,
    upload_screenshot,
    delete_screenshot,
    thumb_url,
)
from utils.ai_mentor import ai_status, calculate_cost, generate_trade_analysis
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
# ეს სახელები ემთხვევა ბაზაში არსებულ ჩანაწერებსა და utils/formulas.py-ს (ENTRY_TERMS / EXIT_TERMS)
SUB_ACTION_TYPES = [
    "ნაწილობრივი დახურვა",
    "სრული დახურვა",
    "დამატებითი შესვლა",
    "ცვლილება",
]
EDIT_STATE_KEY = "edit_sub_id"

_CARD_CSS = """
<style>
/* ქვემოთ ყველა წესი მხოლოდ ჟურნალის სიის რიგებზე მოქმედებს (.trade-row-marker-ის მქონე რიგებზე),
   ამიტომ დეტალების დიალოგის სვეტები და დაშორებები აღარ ირღვევა */
div[data-testid="element-container"]:has(> [data-testid="stHorizontalBlock"] .trade-row-marker) {
    margin-bottom: 2px !important;
    padding-bottom: 0px !important;
}
[data-testid="stVerticalBlock"]:has(.trade-row-marker) {
    gap: 2px !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) {
    align-items: center !important;
    background-color: rgba(255, 255, 255, 0.025) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 4px !important;
    padding: __PADDING__ !important;
    margin: 0px !important;
    width: 100% !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) > div:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    margin-left: auto !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) > [data-testid="stColumn"] {
    width: auto !important;
    flex: unset !important;
    min-width: 0 !important;
}
.trade-thumb-img {
    width: __SIZE__ !important;
    height: __SIZE__ !important;
    min-width: __SIZE__ !important;
    min-height: __SIZE__ !important;
    border-radius: 6px !important;
    object-fit: cover !important;
    object-position: 15% center !important;
    display: block !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
.trade-thumb-placeholder {
    width: __SIZE__ !important;
    height: __SIZE__ !important;
    min-width: __SIZE__ !important;
    min-height: __SIZE__ !important;
    border-radius: 6px !important;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
}
.sub-action-img {
    width: 75px !important;
    height: 75px !important;
    min-width: 75px !important;
    min-height: 75px !important;
    border-radius: 6px !important;
    object-fit: cover !important;
    object-position: center center !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    display: block !important;
}
.sub-action-placeholder {
    width: 75px !important;
    height: 75px !important;
    min-width: 75px !important;
    min-height: 75px !important;
    border-radius: 6px !important;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
.trade-main-text {
    font-size: __FONT_MAIN__;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.1;
}
.trade-sub-text {
    font-size: __FONT_SUB__;
    color: #94a3b8;
    margin-top: 1px;
    display: flex;
    align-items: center;
    gap: 4px;
}
div[data-testid="stPopoverBody"] {
    z-index: 99999 !important;
}
</style>
"""

_SCALES = {
    "small": ("28px", "0.78rem", "0.62rem", "2px 8px"),
    "medium": ("36px", "0.86rem", "0.7rem", "4px 10px"),
    "large": ("46px", "1.05rem", "0.85rem", "8px 12px"),
}


def get_card_css(scale):
  size, font_main, font_sub, padding = _SCALES.get(scale, _SCALES["medium"])
  return (
      _CARD_CSS.replace("__SIZE__", size)
      .replace("__FONT_MAIN__", font_main)
      .replace("__FONT_SUB__", font_sub)
      .replace("__PADDING__", padding)
  )


def inject_card_css():
  """ბარათების CSS გვერდზე ერთხელ ემატება (აღარ მეორდება ყოველ ბარათზე)."""
  st.markdown(
      get_card_css(st.session_state.get("ui_scale", "medium")),
      unsafe_allow_html=True,
  )


def _has_value(value):
  return value is not None and str(value).strip() not in (
      "",
      "None",
      "nan",
      "NaT",
      "<NA>",
      "No Screenshot",
  )


def _txt(value):
  return str(value).strip() if _has_value(value) else ""


def _parse_num(text):
  """ტექსტი -> float. მძიმეც მიიღება (177,605). არასწორზე აბრუნებს None-ს."""
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


def _side_label(side):
  s = str(side).strip().lower()
  if s == "long":
    return "Long"
  if s == "short":
    return "Short"
  return str(side)


def _sort_by_date(frame):
  """ეტაპებს ალაგებს თარიღით (შერეული ფორმატებიც იკითხება) და აბრუნებს თარიღის სვეტის სახელს."""
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
  st.rerun(scope="fragment")  # მხოლოდ დიალოგის შიგთავსი ახლდება, დიალოგი არ იხურება


def _run_ai_analysis(
    trade, sub_actions, trade_id, user_id, mode, cost, opt_detailed, opt_advice
):
  """ქულებს ჯერ ვჭრით (ატომურად), შემდეგ ვაგზავნით AI-ს; თუ ანალიზი ვერ მოხერხდა,
  ზუსტად ეს ჩამოჭრა უკან ბრუნდება."""
  if not user_id:
    st.error("ავტორიზაციის შეცდომა.")
    return

  charge = None
  if cost > 0:
    if not check_has_enough_credits(user_id, cost):
      st.error(f"❌ არ გაქვთ საკმარისი ქულები. საჭიროა: {cost:g}")
      return
    charge = charge_credits(user_id, cost, f"ai_analysis:{trade_id}")
    if not charge.ok:
      st.error(f"❌ {charge.error}")
      return

  lang = st.session_state.get("lang", "ka")
  with st.spinner("მიმდინარეობს AI ანალიზი..."):
    result = generate_trade_analysis(trade, sub_actions, opt_detailed, opt_advice, lang)

  saved = False
  if result.ok:
    saved = update_trade(trade_id, {"ai_analysis": result.analysis, "ai_scores": result.scores})

  if not (result.ok and saved):
    refunded = refund_charge(user_id, charge) if charge else True
    reason = result.error or "შედეგის შენახვა ვერ მოხერხდა."
    suffix = " ქულები დაგიბრუნდათ." if charge and refunded else ""
    st.error(f"❌ {reason}{suffix}")
    if charge and not refunded:
      st.warning("ქულების დაბრუნება ავტომატურად ვერ მოხერხდა. მიმართეთ ადმინისტრატორს.")
    return

  trade["ai_analysis"] = result.analysis
  trade["ai_scores"] = result.scores
  st.success("✅ AI ანალიზი წარმატებით დასრულდა!")
  st.rerun(scope="fragment")




def _render_sub_edit(trade_id, sub, date_col):
  """ეტაპის რედაქტირების ცალკე ეკრანი დეტალების დიალოგის შიგნით (4 ზოლიანი სტრუქტურა პატერნებით და ტრიგერებით)."""
  from database import fetch_settings  # იმპორტი იუზერის პატერნებისა და ტრიგერების ასაღებად

  sub_id = sub.get("Trade ID")
  sub_type = _txt(sub.get("ActionType"))
  is_start = START_ROW_MARK in sub_type
  date_col = date_col or "Entry Date"
  orig_date = _txt(sub.get(date_col))
  parsed_orig = parse_trade_datetime(orig_date)
  shown_date = format_db_datetime(parsed_orig) if not pd.isna(parsed_orig) else orig_date
  current_img = _get_image_url(sub.get("Screenshot"))

  st.markdown("### ✏️ ეტაპის რედაქტირება")
  st.caption(f"{sub.get('Pair', '')} · {sub_type}")

  # ვიღებთ იუზერის ინდივიდუალურ პატერნებს და ტრიგერებს ბაზიდან
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
      new_type = st.selectbox(
          "მოქმედება",
          options,
          index=options.index(sub_type) if sub_type in options else 0,
      )

    # --- ზოლი 1: თარიღი და დრო, შესვლის ფასი, მოცულობა ---
    st.markdown("---")
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    date_txt = r1_c1.text_input(
        "თარიღი და დრო",
        value=shown_date,
        placeholder="YYYY-MM-DD HH:MM:SS",
    )
    price_txt = r1_c2.text_input("შესვლის ფასი", value=_txt(sub.get("Entry Price")))
    qty_txt = r1_c3.text_input("მოცულობა", value=_txt(sub.get("Qty")))

    # --- ზოლი 2: სტოპ ლოსი, თეიქ პროფიტი, რისკი დოლარში ---
    r2_c1, r2_c2, r2_c3 = st.columns(3)
    sl_txt = r2_c1.text_input("სტოპ ლოსი (SL ფასი)", value=_txt(sub.get("SL_Price")))
    tp_txt = r2_c2.text_input("თეიქ პროფიტი (TP ფასი)", value=_txt(sub.get("TP_Price")))
    risk_txt = r2_c3.text_input("რისკი დოლარში (Risk $)", value=_txt(sub.get("Risk ($)")))

    # --- ზოლი 3: აღწერა / კომენტარი, სკრინშოტი (ჰორიზონტალურად გვერდიგვერდ) ---
    orig_desc = _txt(sub.get("Description"))
    desc_txt = st.text_area(
        "აღწერა / კომენტარი (Description)",
        value=orig_desc,
        key=f"edit_sub_desc_{sub_id}",
    )

    # ჰორიზონტალური განლაგება სკრინშოტისთვის და აფლოუდისთვის
    img_col, upload_col = st.columns([1, 2], vertical_alignment="center")
    
    with img_col:
      if current_img:
        st.image(current_img, caption="მიმდინარე სკრინშოტი", width=180)
      else:
        st.caption("სკრინშოტი არ არის")

    with upload_col:
      new_file = st.file_uploader(
          "🖼️ სკრინშოტის შეცვლა",
          type=["png", "jpg", "jpeg"],
          key=f"edit_sub_img_{sub_id}",
      )
        

    # --- ზოლი 4: პატერნი, ტრიგერი, მიმართულება ---
    r4_c1, r4_c2, r4_c3 = st.columns(3)

    # პატერნის არჩევანი
    p_opts = user_patterns if user_patterns else ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"]
    if orig_pattern and orig_pattern not in p_opts:
      p_opts.insert(0, orig_pattern)
    selected_pattern = r4_c1.selectbox(
        "პატერნი",
        p_opts,
        index=p_opts.index(orig_pattern) if orig_pattern in p_opts else 0,
        key=f"edit_pattern_{sub_id}",
    )

    # ტრიგერის არჩევანი
    t_opts = user_triggers if user_triggers else ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]
    if orig_trigger and orig_trigger not in t_opts:
      t_opts.insert(0, orig_trigger)
    selected_trigger = r4_c2.selectbox(
        "ტრიგერი",
        t_opts,
        index=t_opts.index(orig_trigger) if orig_trigger in t_opts else 0,
        key=f"edit_trigger_{sub_id}",
    )

    # მიმართულება (Long / Short)
    side_opts = ["Long", "Short"]
    if orig_side.capitalize() not in side_opts:
      side_opts.insert(0, orig_side)
    selected_side = r4_c3.selectbox(
        "მიმართულება",
        side_opts,
        index=side_opts.index(orig_side.capitalize()) if orig_side.capitalize() in side_opts else 0,
        key=f"edit_side_{sub_id}",
    )

    st.markdown("---")
    b1, b2 = st.columns(2)
    save = b1.form_submit_button(
        "💾 შენახვა", type="primary", use_container_width=True
    )
    cancel = b2.form_submit_button("გაუქმება", use_container_width=True)

  if cancel:
    _close_edit_screen()

  if save:
    required = {"ფასი": price_txt, "მოცულობა": qty_txt, "რისკი": risk_txt}
    parsed = {name: _parse_num(text) for name, text in required.items()}
    errors = [f"არასწორი რიცხვი: {n}" for n, v in parsed.items() if v is None]

    optional = {}
    for name, text in (("SL", sl_txt), ("TP", tp_txt)):
      if not text.strip():
        optional[name] = 0.0
      else:
        value = _parse_num(text)
        if value is None:
          errors.append(f"არასწორი რიცხვი: {name}")
        else:
          optional[name] = value

    new_date = None
    if date_txt.strip() != orig_date:
      parsed_date = parse_trade_datetime(date_txt)
      if pd.isna(parsed_date):
        errors.append("თარიღი ვერ იკითხება (მაგ. 2026-11-10 13:38:02)")
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
        st.toast("ეტაპი განახლდა!", icon="✅")
        _close_edit_screen()

  if not is_start:
    st.divider()
    confirm = st.checkbox(
        "ვადასტურებ ამ ეტაპის წაშლას", key=f"confirm_del_sub_{sub_id}"
    )
    if st.button(
        "🗑️ ეტაპის წაშლა",
        key=f"del_sub_{sub_id}",
        disabled=not confirm,
        use_container_width=True,
    ):
      if delete_trade(sub_id):
        recalc_net_pnl(trade_id)
        st.toast("ეტაპი წაიშალა!", icon="🗑️")
        _close_edit_screen()



@st.dialog("🔍 გარიგების დეტალები და მართვა", width="large")
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

  # --- ეტაპის რედაქტირების ეკრანი (ცალკე "ფანჯარა" დიალოგის შიგნით) ---
  edit_id = st.session_state.get(EDIT_STATE_KEY)
  if edit_id:
    match = sub_actions[sub_actions["Trade ID"] == edit_id]
    if not match.empty:
      _render_sub_edit(trade_id, match.iloc[0], date_col)
      return
    st.session_state.pop(EDIT_STATE_KEY, None)

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  st.markdown(f"### {pair} — **{side}**")

  col_st1, col_st2, col_st3 = st.columns(
      [3, 3, 2], vertical_alignment="center"
  )
  with col_st1:
    new_status = st.toggle(
        "დასრულებული" if is_finalized else "მიმდინარე",
        value=is_finalized,
        key=f"dialog_toggle_fin_{trade_id}",
    )
    if new_status != is_finalized:
      update_trade(trade_id, {"Finalized": str(new_status)})
      recalc_net_pnl(trade_id, clear_if_none=False)
      st.toast("სტატუსი განახლდა!", icon="🔄")
      st.rerun(scope="fragment")

  with col_st2:
    status_badge = "🏁 დასრულებული" if is_finalized else "⚡ მიმდინარე"
    badge_color = GRAY if is_finalized else ORANGE
    st.markdown(
        f"სტატუსი: <b style='color:{badge_color}'>{status_badge}</b>",
        unsafe_allow_html=True,
    )

  with col_st3:
    if st.button(
        "🗑️ გარიგების წაშლა", key=f"dlg_del_{trade_id}", use_container_width=True
    ):
      if delete_trade(trade_id):
        st.success("გარიგება წაიშალა!")
        st.rerun()

  st.divider()

  img_url = _get_image_url(main_screenshot)
  if img_url:
    st.image(img_url, use_container_width=True)
  else:
    st.warning("⚠️ აკლია სკრინშოტი")

  st.divider()

  # --- ეტაპების ბარათები: სამი გვერდიგვერდ, მარცხნიდან მარჯვნივ, ქრონოლოგიურად ---
  st.markdown("### 📊 გარიგების მართვა / დამატებითი ქმედებები")

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
                st.markdown(
                    f"<img src='{sub_img}' class='sub-action-img'"
                    " loading='lazy'>",
                    unsafe_allow_html=True,
                )
              else:
                st.markdown(
                    "<div class='sub-action-placeholder'>📁</div>",
                    unsafe_allow_html=True,
                )
            with c_desc:
              st.markdown(f"**{sub_type}**")
              st.markdown(f"ფასი: `{sub_price}`")
              st.markdown(f"მოცულობა: `{sub_qty}`")
              st.caption(
                  f"📅 {_pretty_date(sub_date) if _has_value(sub_date) else ''}"
              )

            if st.button(
                "✏️ რედაქტირება",
                key=f"btn_edit_sub_{sub_id}",
                use_container_width=True,
            ):
              st.session_state[EDIT_STATE_KEY] = sub_id
              st.rerun(scope="fragment")
  else:
    st.info("ამ გარიგებაზე დამატებითი ქმედებები ჯერ არ ფიქსირდება.")



    
  with st.expander("➕ ახალი ქმედების დამატება (ნაწილობრივი/სრული გასვლა, დამატება)"):
    with st.form(key=f"form_add_sub_{trade_id}", clear_on_submit=True):
      # 1. პირველი ველი: თარიღი და დრო
      add_date = st.text_input(
          "თარიღი და დრო",
          value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          key=f"add_sub_date_{trade_id}",
      )

      # 2. მეორე ველი: მოქმედების ტიპი
      add_type = st.selectbox("მოქმედების ტიპი", SUB_ACTION_TYPES)

      # 3 & 4. ფასი და მოცულობა გვერდი-გვერდ
      a1, a2 = st.columns(2)
      add_price = a1.number_input("ფასი", value=0.0, format="%.5f")
      add_qty = a2.number_input("მოცულობა (Qty)", value=1.0, format="%.2f")
      
      # 5. აღწერა / კომენტარი
      add_description = st.text_area(
          "აღწერა / კომენტარი (Description)",
          value="",
          key=f"add_sub_desc_{trade_id}",
      )

      # 6. სკრინშოტი
      add_file = st.file_uploader(
          "შუალედური სკრინშოტი (არასავალდებულო)",
          type=["png", "jpg", "jpeg"],
          key=f"sub_img_up_{trade_id}",
      )
      
      add_submit = st.form_submit_button(
          "მონაცემის დამატება", use_container_width=True
      )

    if add_submit:
      parsed_add_date = parse_trade_datetime(add_date)

      if pd.isna(parsed_add_date):
        st.error("თარიღი ვერ იკითხება (მაგ. 2026-11-10 13:38:02 ან Nov 10, 1:38:02 PM)")
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
          st.toast("მონაცემი დაემატა!", icon="✅")
          st.rerun(scope="fragment")
    
  st.divider()

  # --- AI ასისტენტი ---
  st.markdown("### 🤖 AI ასისტენტი")
  user_id = st.session_state.user.id if st.session_state.user else None
  mode = ai_status()

  if mode == "disabled":
    st.info("AI მენტორი ჯერ ჩართული არ არის. ქულები არ იხარჯება.")
  else:
    current_credits = get_user_credits_cached(user_id) if user_id else 0.0
    st.caption(f"💳 ბალანსი: **{current_credits:g} ქულა**")
    if mode == "demo":
      st.caption("🧪 დემო რეჟიმი: პასუხი სატესტოა და ქულები არ იხარჯება.")

    opt_detailed = st.toggle("ვრცელი პასუხი (+2 ქულა)", key=f"ai_opt_det_{trade_id}")
    opt_advice = st.toggle("AI რჩევა (+2 ქულა)", key=f"ai_opt_adv_{trade_id}")
    total_cost = 0.0 if mode == "demo" else calculate_cost(opt_detailed, opt_advice)

    if st.button(
        f"🚀 გაგზავნა: {total_cost:g} ქულა",
        key=f"ai_send_{trade_id}",
        use_container_width=True,
    ):
      _run_ai_analysis(
          trade, sub_actions, trade_id, user_id, mode, total_cost, opt_detailed, opt_advice
      )

  stored_analysis = trade.get("ai_analysis")
  if _has_value(stored_analysis):
    with st.expander("🤖 AI შეფასების შედეგი", expanded=True):
      st.markdown(stored_analysis)

  st.divider()

  breakdown = pnl_breakdown(trade, sub_actions)
  st.markdown("**🧮 Net P/L-ის გაანგარიშება**")
  if breakdown is None:
    st.caption("გასვლის (დახურვის) ეტაპი ჯერ არ არის, ამიტომ Net P/L არ ითვლება.")
  else:
    lines = [
        f"- შესვლა (საშუალო): `{breakdown['entry_avg']:.5f}` ×"
        f" `{breakdown['entry_qty']:g}`",
    ]
    if breakdown["exit_avg"] is not None:
      lines.append(
          f"- გასვლა (შეწონილი): `{breakdown['exit_avg']:.5f}` ×"
          f" `{breakdown['exit_qty']:g}` · დახურული წილი:"
          f" `{breakdown['closed_fraction'] * 100:.0f}%`"
      )
    if breakdown["method"] == "R":
      lines.append(
          f"- სტოპი (SL): `{breakdown['stop_price']:.5f}` · დისტანცია:"
          f" `{breakdown['stop_dist']:.5f}`"
      )
      lines.append(f"- კოეფიციენტი (R): `{breakdown['r_multiple']:.4f}`")
    lines.append(
        f"- რისკი: `{breakdown['risk']:g}$` → **Net P/L ="
        f" {breakdown['pnl']:+.2f}$**"
    )
    st.markdown("\n".join(lines))
    if breakdown["method"] == "legacy":
      st.warning(
          "⚠️ SL ფასი არ არის მითითებული ან არასწორია (არასწორ მხარესაა / ძალიან"
          " შორსაა / ფორმის ნაგულისხმევია), ამიტომ გამოიყენება ძველი %-ზე"
          " დაფუძნებული გამოთვლა. ჩაასწორე Start Row-ის SL ✏️-ით ზემოთ."
      )

  st.divider()
  if st.button("✅ დახურვა", key=f"close_dlg_{trade_id}", use_container_width=True):
    st.rerun()


def render_trade_card(trade, df, subs=None, pnl=None):
  """subs და pnl გადმოცემის შემთხვევაში თავიდან აღარ ითვლება (journal.py ერთხელ ითვლის ყველასთვის)."""
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = html.escape(str(trade.get("Pair", "N/A")))  # HTML-ში ჩასმამდე
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  screenshot = trade.get("Screenshot")

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  if pnl is None:
    if subs is None:
      subs = df[df["Parent Trade ID"] == trade_id]
    pnl = calculate_net_pnl(trade, subs)
    if pnl is None:
      raw_net = trade.get("Net P/L")
      pnl = to_float(raw_net) if _has_value(raw_net) else 0.0

  state_key = f"mode_{trade_id}"
  current_mode = st.session_state.get(state_key, None)

  if is_finalized:
    pnl_color = GREEN if pnl > 0 else (RED if pnl < 0 else GRAY)
    status_indicator = (
        f"<span style='color:{pnl_color}; font-weight:600;'>{pnl:+.2f}$</span>"
    )
  else:
    status_indicator = (
        f"<span style='background-color: {ORANGE}; color: white; font-size:"
        " 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight:"
        " 500;'>მიმდინარე</span>"
    )

  img_url = _get_image_url(screenshot)
  if img_url:
    thumb_html = (
        f"<img src='{html.escape(str(thumb_url(img_url)), quote=True)}' class='trade-thumb-img' loading='lazy'"
        " decoding='async'>"
    )
  else:
    thumb_html = "<div class='trade-thumb-placeholder'>📁</div>"

  col_thumb, col_info, col_menu = st.columns(
      [0.7, 8.8, 0.5], vertical_alignment="center"
  )

  with col_thumb:
    st.markdown(thumb_html, unsafe_allow_html=True)

  with col_info:
    # trade-row-marker: მისით CSS ცნობს ჟურნალის სიის რიგს (დიალოგის სვეტებს არ ეხება)
    st.markdown(
        f"""
        <div style='display: flex; flex-direction: column; justify-content: center; min-width: 0;'>
            <span class='trade-row-marker'></span>
            <div class='trade-main-text'>
                <span>{pair}</span>
                {status_indicator}
            </div>
            <div class='trade-sub-text'>
                <span>{_side_label(side)}</span>
                <span>•</span>
                <span>{_pretty_date(entry_date)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col_menu:
    with st.popover("⋯"):
      if st.button("დეტალები", key=f"det_menu_{trade_id}", use_container_width=True):
        st.session_state.pop(EDIT_STATE_KEY, None)  # დიალოგი ყოველთვის მთავარი ეკრანით იხსნება
        show_trade_details_dialog(trade)

      if st.button("წაშლა", key=f"del_menu_{trade_id}", use_container_width=True):
        st.session_state[state_key] = "delete"
        st.rerun()

  if current_mode == "delete":
    st.error("⚠️ ნამდვილად გსურთ გარიგების წაშლა?")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
      if st.button(
          "დიახ", key=f"conf_del_{trade_id}", use_container_width=True
      ):
        if delete_trade(trade_id):
          st.success("წაიშალა!")
          del st.session_state[state_key]
          st.rerun()
    with col_d2:
      if st.button(
          "გაუქმება", key=f"canc_del_{trade_id}", use_container_width=True
      ):
        del st.session_state[state_key]
        st.rerun()
