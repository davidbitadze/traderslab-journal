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
from utils.ai_mentor import generate_trade_analysis
from utils.credits import (
    check_has_enough_credits,
    deduct_credits,
    get_user_credits_cached,
)
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
  else:
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
.sub-action-img {{
    width: 90px !important;
    height: 90px !important;
    min-width: 90px !important;
    min-height: 90px !important;
    border-radius: 6px !important;
    object-fit: cover !important;
    object-position: center center !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    display: block !important;
}}
.sub-action-placeholder {{
    width: 90px !important;
    height: 90px !important;
    min-width: 90px !important;
    min-height: 90px !important;
    border-radius: 6px !important;
    background: rgba(255,255,255,0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    border: 1px solid rgba(255,255,255,0.1) !important;
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


def inject_card_css():
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
  sub_actions = df[df["Parent Trade ID"] == trade_id]

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

  # მთავარი სკრინშოტის ვიზუალი (ატვირთვის ღილაკის გარეშე, რადგან ინდივიდუალურ ბარათებში ხდება)
  img_url = _get_image_url(main_screenshot)
  if img_url:
    st.image(img_url, use_container_width=True)
  else:
    st.warning("⚠️ აკლია სკრინშოტი")

  st.divider()

  # --- 3-სვეტიანი ბარათების განლაგება მკაცრი მარცხენა ალაინით ---
  st.markdown("### 📊 გარიგების მართვა / დამატებითი ქმედებები")
  
  if not sub_actions.empty:
    sub_list = list(sub_actions.iterrows())
    for i in range(0, len(sub_list), 3):
      cols = st.columns(3)
      for j in range(3):
        if i + j < len(sub_list):
          idx, row = sub_list[i + j]
          sub_id = row.get("Trade ID") or row.get("id") or idx
          sub_type = row.get("Action Type", row.get("action_type", "Action"))
          sub_price = row.get("Price", row.get("price", 0.0))
          sub_qty = row.get("Quantity", row.get("quantity", 0.0))
          sub_date = row.get("Date", row.get("date", ""))
          sub_img = _get_image_url(row.get("Screenshot", row.get("screenshot")))
          
          with cols[j]:
            with st.container(border=True):
              col_img, col_desc = st.columns([1, 2], vertical_alignment="center")
              with col_img:
                if sub_img:
                  st.markdown(f"<img src='{sub_img}' class='sub-action-img'>", unsafe_allow_html=True)
                else:
                  st.markdown("<div class='sub-action-placeholder'>📁</div>", unsafe_allow_html=True)
              with col_desc:
                st.markdown(f"**{sub_type}**")
                st.markdown(f"ფასი: `{sub_price}`")
                st.markdown(f"მოცულობა: `{sub_qty}`")
                st.caption(f"📅 {_pretty_date(sub_date)}")

              edit_sub_key = f"edit_sub_mode_{sub_id}"
              if st.button("✏️ რედაქტირება", key=f"btn_edit_sub_{sub_id}", use_container_width=True):
                st.session_state[edit_sub_key] = not st.session_state.get(edit_sub_key, False)
                st.rerun(scope="fragment")

              if st.session_state.get(edit_sub_key, False):
                with st.container(border=True):
                  new_sub_type = st.selectbox("მოქმედება", ["Partial Exit", "Full Exit", "Add Position"], index=["Partial Exit", "Full Exit", "Add Position"].index(sub_type) if sub_type in ["Partial Exit", "Full Exit", "Add Position"] else 0, key=f"stype_{sub_id}")
                  new_sub_price = st.number_input("ფასი", value=float(sub_price or 0.0), format="%.5f", key=f"sprice_{sub_id}")
                  new_sub_qty = st.number_input("მოცულობა", value=float(sub_qty or 0.0), format="%.2f", key=f"sqty_{sub_id}")
                  
                  new_sub_file = st.file_uploader("სკრინშოტის შეცვლა", type=["png", "jpg", "jpeg"], key=f"supimg_{sub_id}")
                  
                  col_sb1, col_sb2 = st.columns(2)
                  with col_sb1:
                    if st.button("შენახვა", key=f"ssave_{sub_id}", use_container_width=True):
                      payload = {
                          "Action Type": new_sub_type,
                          "Price": new_sub_price,
                          "Quantity": new_sub_qty
                      }
                      if new_sub_file is not None:
                        ext = os.path.splitext(new_sub_file.name)[1].lower() or ".png"
                        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        file_safe_name = f"sub_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
                        up_url = upload_screenshot(new_sub_file, file_name=file_safe_name)
                        if up_url:
                          payload["Screenshot"] = up_url
                      
                      update_trade(sub_id, payload)
                      st.session_state[edit_sub_key] = False
                      st.success("განახლდა!")
                      st.rerun()
                  with col_sb2:
                    if st.button("გაუქმება", key=f"scanc_{sub_id}", use_container_width=True):
                      st.session_state[edit_sub_key] = False
                      st.rerun()
  else:
    st.info("ამ გარიგებაზე დამატებითი ქმედებები ჯერ არ ფიქსირდება.")

  with st.expander("➕ ახალი ქმედების დამატება (ნაწილობრივი/სრული გასვლა, დამატება)"):
    sub_type = st.selectbox("მოქმედების ტიპი", ["Partial Exit", "Full Exit", "Add Position"], key=f"sub_type_{trade_id}")
    sub_price = st.number_input("ფასი", value=0.0, format="%.5f", key=f"sub_price_{trade_id}")
    sub_qty = st.number_input("მოცულობა (Qty)", value=1.0, format="%.2f", key=f"sub_qty_{trade_id}")
    
    sub_img_file = st.file_uploader("შუალედური სკრინშოტი (არასავალდებულო)", type=["png", "jpg", "jpeg"], key=f"sub_img_up_{trade_id}")
    
    if st.button("მონაცემის დამატება", key=f"add_sub_btn_{trade_id}", use_container_width=True):
      sub_screenshot_url = None
      if sub_img_file is not None:
        ext = os.path.splitext(sub_img_file.name)[1].lower() or ".png"
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_safe_name = f"sub_{pair}_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
        sub_screenshot_url = upload_screenshot(sub_img_file, file_name=file_safe_name)

      sub_payload = {
          "Parent Trade ID": trade_id,
          "Action Type": sub_type,
          "Price": sub_price,
          "Quantity": sub_qty,
          "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          "Screenshot": sub_screenshot_url if sub_screenshot_url else None
      }
      insert_trade(sub_payload)
      recalc_net_pnl(trade_id, clear_if_none=False)
      st.success("მონაცემი დაემატა!")
      st.rerun(scope="fragment")

  st.divider()

  # --- AI ასისტენტი ---
  st.markdown("### 🤖 AI ასისტენტი")
  user_id = st.session_state.user.id if st.session_state.user else None
  current_credits = get_user_credits_cached(user_id) if user_id else 0.0

  st.caption(f"💳 ბალანსი: **{current_credits:g} ქულა**")

  opt_detailed = st.toggle("ვრცელი პასუხი (+2 ქულა)", key=f"ai_opt_det_{trade_id}")
  opt_advice = st.toggle("AI რჩევა (+2 ქულა)", key=f"ai_opt_adv_{trade_id}")

  base_cost = 1.0
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
        with st.spinner("მიმდინარეობს AI ანალიზი..."):
          analysis_text, scores_text = generate_trade_analysis(
              trade, sub_actions, opt_detailed, opt_advice
          )
          update_trade(
              trade_id,
              {"ai_analysis": analysis_text, "ai_scores": scores_text},
          )
          trade["ai_analysis"] = analysis_text
          trade["ai_scores"] = scores_text

        st.success("✅ AI ანალიზი წარმატებით დასრულდა!")
        st.rerun(scope="fragment")

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

  st.divider()
  if st.button("✅ დახურვა", key=f"close_dlg_{trade_id}", use_container_width=True):
    st.rerun()


def render_trade_card(trade, df, subs=None, pnl=None):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
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
        f"<img src='{img_url}' class='trade-thumb-img' loading='lazy'"
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
    st.markdown(
        f"""
        <div style='display: flex; flex-direction: column; justify-content: center; min-width: 0;'>
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
