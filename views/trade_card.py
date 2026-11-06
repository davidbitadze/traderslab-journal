from datetime import datetime
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
)
from utils.credits import check_has_enough_credits, deduct_credits, get_user_credits
from utils.formulas import calculate_net_pnl, pnl_breakdown, to_float

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"
ORANGE = "#f97316"


def get_card_css(scale):
  if scale == "small":
    size = "28px"
    font_main = "0.78rem"
    font_sub = "0.62rem"
    padding = "2px 8px"
  elif scale == "large":
    size = "46px"
    font_main = "1.05rem"
    font_sub = "0.85rem"
    padding = "8px 12px"
  else:  # medium (default)
    size = "36px"
    font_main = "0.86rem"
    font_sub = "0.7rem"
    padding = "4px 10px"

  return f"""
<style>
div[data-testid="element-container"]:has(> [data-testid="stHorizontalBlock"]) {{
    margin-bottom: 2px !important;
    padding-bottom: 0px !important;
}}
[data-testid="stVerticalBlock"] {{
    gap: 2px !important;
}}
[data-testid="stHorizontalBlock"] {{
    align-items: center !important;
    background-color: rgba(255, 255, 255, 0.025) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    border-radius: 4px !important;
    padding: {padding} !important;
    margin: 0px !important;
    width: 100% !important;
}}
[data-testid="stHorizontalBlock"] > div:last-child {{
    display: flex !important;
    justify-content: flex-end !important;
    margin-left: auto !important;
}}
[data-testid="stColumn"] {{
    width: auto !important;
    flex: unset !important;
    min-width: 0 !important;
}}
.trade-thumb-img {{
    width: {size} !important;
    height: {size} !important;
    min-width: {size} !important;
    min-height: {size} !important;
    border-radius: 6px !important;
    object-fit: cover !important;
    object-position: 15% center !important;
    display: block !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}}
.trade-thumb-placeholder {{
    width: {size} !important;
    height: {size} !important;
    min-width: {size} !important;
    min-height: {size} !important;
    border-radius: 6px !important;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.95rem;
}}
.trade-main-text {{
    font-size: {font_main};
    font-weight: 600;
    color: #ffffff;
    display: flex;
    align-items: center;
    gap: 6px;
    line-height: 1.1;
}}
.trade-sub-text {{
    font-size: {font_sub};
    color: #94a3b8;
    margin-top: 1px;
    display: flex;
    align-items: center;
    gap: 4px;
}}
div[data-testid="stPopoverBody"] {{
    z-index: 99999 !important;
}}
</style>
"""


def _has_value(value):
  return value is not None and str(value).strip() not in (
      "",
      "None",
      "nan",
      "NaT",
      "<NA>",
      "No Screenshot",
  )


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
  try:
    return pd.to_datetime(value).strftime("%d %b %Y, %H:%M")
  except Exception:
    return str(value)


def _side_label(side):
  s = str(side).strip().lower()
  if s == "long":
    return "Long"
  if s == "short":
    return "Short"
  return str(side)


def _parse_num(text):
  """ტექსტი -> float. მძიმეც მიიღება (177,605). არასწორზე აბრუნებს None-ს."""
  try:
    return float(str(text).strip().replace(",", "."))
  except (ValueError, TypeError):
    return None


def _txt(value):
  return str(value).strip() if _has_value(value) else ""


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


def recalc_all_net_pnl(df=None):
  """ყველა გარიგების Net P/L-ს ხელახლა ითვლის და ბაზაში წერს მხოლოდ იქ, სადაც შეიცვალა.

  იძახება ჟურნალის ჩატვირთვისას (ერთხელ სესიაზე), რომ ბაზაში ძველი რიცხვები არ
  დარჩეს.
  """
  if df is None:
    df = fetch_trades()
  if df.empty:
    return 0
  mains = df[
      df["ActionType"].astype(str).str.contains("Start Row", case=False, na=False)
  ]
  changed = 0
  for _, trade in mains.iterrows():
    trade_id = trade.get("Trade ID")
    subs = df[df["Parent Trade ID"] == trade_id]
    net = calculate_net_pnl(trade, subs)
    if net is None:  # გასვლა არ არის: არსებულ მნიშვნელობას არ ვეხებით
      continue
    old = trade.get("Net P/L")
    if _has_value(old) and abs(to_float(old) - net) < 0.005:
      continue
    if update_trade(trade_id, {"Net P/L": str(net)}):
      changed += 1
  return changed


@st.dialog("🔍 გარიგების დეტალები და მართვა", width="large")
def show_trade_details_dialog(trade, df):
  df = fetch_trades()
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

  fresh = df[df["Trade ID"] == trade_id]
  if not fresh.empty:
    trade = fresh.iloc[0].to_dict()

  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  main_screenshot = trade.get("Screenshot")
  sub_actions = df[df["Parent Trade ID"] == trade_id]

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  st.markdown(f"### {pair} — **{side}**")

  col_st1, col_st2, col_st3 = st.columns(
      [2.5, 2.5, 2], vertical_alignment="center"
  )
  with col_st1:
    new_status = st.toggle(
        "დასრულებული" if is_finalized else "მიმდინარე",
        value=is_finalized,
        key=f"dialog_toggle_fin_{trade_id}",
    )
    if new_status != is_finalized:
      update_trade(trade_id, {"Finalized": str(new_status)})
      recalc_net_pnl(
          trade_id, clear_if_none=False
      )  # სტატუსის შეცვლისას Net P/L ახლდება
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

  new_img = st.file_uploader(
      "🖼️ სკრინშოტის შეცვლა / ატვირთვა",
      type=["png", "jpg", "jpeg"],
      key=f"up_img_{trade_id}",
  )
  if new_img is not None:
    ext = os.path.splitext(new_img.name)[1].lower() or ".png"
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_safe_name = f"{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
    uploaded_url = upload_screenshot(new_img, file_name=file_safe_name)
    if uploaded_url:
      update_trade(trade_id, {"Screenshot": uploaded_url})
      st.toast("სკრინშოტი განახლდა!", icon="🖼️")
      st.rerun(scope="fragment")

  st.divider()

  # --- AI ასისტენტი (Glide-ის სტილში: ბალანსი, ტოგლები და დინამიური ღირებულება) ---
  st.markdown("### 🤖 AI ასისტენტი")
  user_id = st.session_state.user.id if st.session_state.user else None
  current_credits = get_user_credits(user_id) if user_id else 0.0

  st.caption(f"💳 ბალანსი: **{current_credits:g} ქულა**")

  opt_detailed = st.toggle("ვრცელი პასუხი (+2 ქულა)", key=f"ai_opt_det_{trade_id}")
  opt_advice = st.toggle("AI რჩევა (+2 ქულა)", key=f"ai_opt_adv_{trade_id}")

  base_cost = 1.0  # საბაზისო ანალიზი
  total_cost = (
      base_cost
      + (2.0 if opt_detailed else 0.0)
      + (2.0 if opt_advice else 0.0)
  )

  if st.button(
      f"🚀 გაგზავნა: {total_cost:g} ქულა",
      key=f"ai_send_{trade_id}",
      use_container_width=True,
  ):
    if not user_id:
      st.error("ავტორიზაციის შეცდომა.")
    elif not check_has_enough_credits(user_id, total_cost):
      st.error(
          f"❌ არ გაქვთ საკმარისი ქულები. საჭიროა: {total_cost:g}, თქვენ გაქვთ:"
          f" {current_credits:g}"
      )
    else:
      if deduct_credits(user_id, total_cost):
        st.success(
            "✅ ქულები წარმატებით ჩამოიჭრა! მიმდინარეობს AI ანალიზი..."
        )
        # აქ დაემატება OpenAI / Claude API გამოძახება
        st.rerun(scope="fragment")

  st.divider()

  td_current = trade.get("Entry Date")
  td_text = st.text_input(
      "🗓️ გარიგების თარიღი და დრო",
      value=str(td_current) if _has_value(td_current) else "",
      placeholder="YYYY-MM-DD HH:MM:SS",
      key=f"td_text_{trade_id}",
  )
  td_parsed = (
      pd.to_datetime(td_text, errors="coerce") if td_text.strip() else pd.NaT
  )
  td_invalid = bool(pd.isna(td_parsed))

  col_td1, col_td2 = st.columns([4, 2], vertical_alignment="center")
  with col_td1:
    if td_invalid:
      st.caption("⚠️ თარიღი ვერ იკითხება.")
    else:
      st.caption(
          f"✅ წაიკითხება როგორც: {td_parsed.strftime('%d %b %Y, %H:%M:%S')}"
      )
  with col_td2:
    if st.button(
        "💾 შენახვა",
        key=f"td_save_{trade_id}",
        use_container_width=True,
        disabled=td_invalid,
    ):
      stamp = td_parsed.strftime("%Y-%m-%d %H:%M:%S")
      if update_trade(trade_id, {"Entry Date": stamp}):
        st.toast("თარიღი შენახულია!", icon="🗓️")
        st.rerun(scope="fragment")

  st.divider()

  # --- Net P/L-ის გაანგარიშება (ყველა ნაბიჯი თვალსაჩინოდ) ---
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
        f" {breakdown['pnl']:+.2f}\$**"
    )
    st.markdown("\n".join(lines))
    if breakdown["method"] == "legacy":
      st.warning(
          "⚠️ SL ფასი არ არის მითითებული ან არასწორია (არასწორ მხარესაა / ძალიან"
          " შორსაა / ფორმის ნაგულისხმევია), ამიტომ გამოიყენება ძველი %-ზე დაფუძნებული"
          " გამოთვლა. ჩაასწორე Start Row-ის SL ✏️-ით ქვემოთ."
      )

  st.divider()

  # --- დამატებითი ეტაპების ისტორია და მართვა ---
  st.markdown("**📋 ეტაპების ისტორია და მართვა:**")

  if not sub_actions.empty:
    active_edit_sub = st.session_state.get("active_edit_sub")
    for _, sub in sub_actions.iterrows():
      sub_id = sub.get("Trade ID")
      col_h1, col_h2, col_h3 = st.columns([7, 1, 1])
      with col_h1:
        st.info(
            f"• **{sub.get('ActionType')}** | ფასი: {sub.get('Entry Price')} |"
            f" მოც.: {sub.get('Qty')} | დრო: {sub.get('Entry Date')}"
        )
      with col_h2:
        if st.button("✏️", key=f"edit_sub_{sub_id}"):
          st.session_state["active_edit_sub"] = sub_id
          st.rerun(scope="fragment")
      with col_h3:
        if st.button("🗑️", key=f"del_sub_{sub_id}"):
          if delete_trade(sub_id):
            recalc_net_pnl(trade_id)
            st.rerun(scope="fragment")

      if active_edit_sub == sub_id:
        with st.form(key=f"form_edit_sub_{sub_id}"):
          st.markdown(f"**ეტაპის რედაქტირება: {sub.get('ActionType')}**")
          is_start_row = "Start Row" in str(sub.get("ActionType", ""))
          new_price = st.text_input("ფასი", value=_txt(sub.get("Entry Price")))
          new_qty = st.text_input("მოცულობა", value=_txt(sub.get("Qty")))
          if is_start_row:
            new_sl = st.text_input(
                "სტოპ ლოსი (SL ფასი)", value=_txt(sub.get("SL_Price"))
            )
            new_risk = st.text_input(
                "რისკი დოლარში (Risk \$)", value=_txt(sub.get("Risk (\$)"))
            )
          if st.form_submit_button("💾 ცვლილების შენახვა"):
            fields = {"ფასი": new_price, "მოცულობა": new_qty}
            if is_start_row:
              fields.update({"SL": new_sl, "რისკი": new_risk})
            parsed = {name: _parse_num(text) for name, text in fields.items()}
            bad = [name for name, val in parsed.items() if val is None]
            if bad:
              st.error(f"არასწორი რიცხვი: {', '.join(bad)}. არაფერი შეინახა.")
            else:
              data = {
                  "Entry Price": str(parsed["ფასი"]),
                  "Qty": str(parsed["მოცულობა"]),
              }
              if is_start_row:
                data["SL_Price"] = str(parsed["SL"])
                data["Risk (\$)"] = str(parsed["რისკი"])
              update_trade(sub_id, data)
              st.session_state["active_edit_sub"] = None
              recalc_net_pnl(trade_id)
              st.success("განახლდა!")
              st.rerun(scope="fragment")
  else:
    st.caption("დამატებითი ეტაპები არ არის.")

  with st.form(key=f"form_add_sub_{trade_id}", clear_on_submit=True):
    st.markdown("**➕ ახალი ეტაპის დამატება:**")

    act_type = st.selectbox(
        "მოქმედების ტიპი",
        [
            "ნაწილობრივი დახურვა",
            "სრული დახურვა",
            "ცვლილება",
            "დამატ
