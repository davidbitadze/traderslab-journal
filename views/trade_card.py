import os
import uuid
from datetime import datetime
from database import (
    delete_trade,
    insert_trade,
    update_trade,
    fetch_trades,
    upload_screenshot,
)
import pandas as pd
import streamlit as st
from utils.formulas import calculate_net_pnl, to_float

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
      "", "None", "nan", "NaT", "<NA>", "No Screenshot"
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

def recalc_net_pnl(parent_id):
  df = fetch_trades()
  if df.empty:
    return
  main_df = df[df["Trade ID"] == parent_id]
  if main_df.empty:
    return
  subs = df[df["Parent Trade ID"] == parent_id]
  net = calculate_net_pnl(main_df.iloc[0], subs)
  update_trade(parent_id, {"Net P/L": None if net is None else str(net)})

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
  
  col_st1, col_st2, col_st3 = st.columns([2.5, 2.5, 2], vertical_alignment="center")
  with col_st1:
    new_status = st.toggle(
        "დასრულებული" if is_finalized else "მიმდინარე",
        value=is_finalized,
        key=f"dialog_toggle_fin_{trade_id}"
    )
    if new_status != is_finalized:
      update_trade(trade_id, {"Finalized": str(new_status)})
      st.toast("სტატუსი განახლდა!", icon="🔄")
      st.rerun(scope="fragment")

  with col_st2:
    status_badge = "🏁 დასრულებული" if is_finalized else "⚡ მიმდინარე"
    badge_color = GRAY if is_finalized else ORANGE
    st.markdown(f"სტატუსი: <b style='color:{badge_color}'>{status_badge}</b>", unsafe_allow_html=True)

  with col_st3:
    if st.button("🗑️ გარიგების წაშლა", key=f"dlg_del_{trade_id}", use_container_width=True):
      if delete_trade(trade_id):
        st.success("გარიგება წაიშალა!")
        st.rerun()

  st.divider()

  img_url = _get_image_url(main_screenshot)
  if img_url:
    st.image(img_url, use_container_width=True)
  
  new_img = st.file_uploader("🖼️ სკრინშოტის შეცვლა / ატვირთვა", type=["png", "jpg", "jpeg"], key=f"up_img_{trade_id}")
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

  td_current = trade.get("Entry Date")
  td_text = st.text_input(
      "🗓️ გარიგების თარიღი და დრო",
      value=str(td_current) if _has_value(td_current) else "",
      placeholder="YYYY-MM-DD HH:MM:SS",
      key=f"td_text_{trade_id}",
  )
  td_parsed = pd.to_datetime(td_text, errors="coerce") if td_text.strip() else pd.NaT
  td_invalid = bool(pd.isna(td_parsed))

  col_td1, col_td2 = st.columns([4, 2], vertical_alignment="center")
  with col_td1:
    if td_invalid:
      st.caption("⚠️ თარიღი ვერ იკითხება.")
    else:
      st.caption(f"✅ წაიკითხება როგორც: {td_parsed.strftime('%d %b %Y, %H:%M:%S')}")
  with col_td2:
    if st.button("💾 შენახვა", key=f"td_save_{trade_id}", use_container_width=True, disabled=td_invalid):
      stamp = td_parsed.strftime("%Y-%m-%d %H:%M:%S")
      if update_trade(trade_id, {"Entry Date": stamp}):
        st.toast("თარიღი შენახულია!", icon="🗓️")
        st.rerun(scope="fragment")

  st.divider()

  # --- დამატებითი ეტაპების ისტორია და მართვა ---
  st.markdown("**📋 ეტაპების ისტორია და მართვა:**")
  
  if not sub_actions.empty:
    active_edit_sub = st.session_state.get("active_edit_sub")
    for _, sub in sub_actions.iterrows():
      sub_id = sub.get("Trade ID")
      col_h1, col_h2, col_h3 = st.columns([7, 1, 1])
      with col_h1:
        st.info(f"• **{sub.get('ActionType')}** | ფასი: {sub.get('Entry Price')} | მოც.: {sub.get('Qty')} | დრო: {sub.get('Entry Date')}")
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
          new_price = st.text_input("ფასი", value=str(sub.get('Entry Price', 0)))
          new_qty = st.text_input("მოცულობა", value=str(sub.get('Qty', 0)))
          if st.form_submit_button("💾 ცვლილების შენახვა"):
            update_trade(sub_id, {"Entry Price": to_float(new_price), "Qty": to_float(new_qty)})
            st.session_state["active_edit_sub"] = None
            recalc_net_pnl(trade_id)
            st.success("განახლდა!")
            st.rerun(scope="fragment")
  else:
    st.caption("დამატებითი ეტაპები არ არის.")

  # ფორმა ახალი დამატებითი ეტაპის (Action) დასამატებლად თარიღით და სწორი ქართული თანმიმდევრობით
  with st.form(key=f"form_add_sub_{trade_id}", clear_on_submit=True):
    st.markdown("**➕ ახალი ეტაპის დამატება:**")
    
    act_type = st.selectbox(
        "მოქმედების ტიპი",
        [
            "ნაწილობრივი დახურვა",
            "სრული დახურვა",
            "ცვლილება",
            "დამატებითი შესვლა"
        ],
        key=f"add_act_type_{trade_id}"
    )

    sub_date = st.text_input(
        "ეტაპის თარიღი და დრო",
        value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        key=f"add_sub_date_{trade_id}"
    )
        
    col_sub1, col_sub2 = st.columns(2)
    with col_sub1:
      sub_price = st.number_input("ფასი (Price)", value=0.0, step=0.0001, format="%.4f")
    with col_sub2:
      sub_qty = st.number_input("მოცულობა / ოდენობა (Qty)", value=1.0, step=0.1)

    
    sub_desc = st.text_input("შენიშვნა / აღწერა", key=f"add_sub_desc_{trade_id}")
    sub_img = st.file_uploader("🖼️ ეტაპის სკრინშოტი (არასავალდებულო)", type=["png", "jpg", "jpeg"], key=f"add_sub_img_{trade_id}")

    if st.form_submit_button("➕ ეტაპის დამატება გარიგებაში", use_container_width=True):
      sub_screenshot_url = ""
      if sub_img is not None:
        ext = os.path.splitext(sub_img.name)[1].lower() or ".png"
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        sub_file_name = f"{pair}_sub_{stamp}_{uuid.uuid4().hex[:6]}{ext}"
        sub_screenshot_url = upload_screenshot(sub_img, file_name=sub_file_name) or ""

      new_sub_trade = {
          "Trade ID": str(uuid.uuid4()),
          "Parent Trade ID": trade_id,
          "Pair": pair,
          "Side": side,
          "ActionType": act_type,
          "Entry Price": str(sub_price),
          "Qty": str(sub_qty),
          "Description": sub_desc,
          "Screenshot": sub_screenshot_url,
          "Entry Date": sub_date,
          "Finalized": "false"
      }
      if insert_trade(new_sub_trade):
        recalc_net_pnl(trade_id)
        st.success("ეტაპი წარმატებით დაემატა!")
        st.rerun(scope="fragment")

  st.divider()
  if st.button("✅ დახურვა", key=f"close_dlg_{trade_id}", use_container_width=True):
    st.rerun()

def render_trade_card(trade, df):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = trade.get("Pair", "N/A")
  side = trade.get("Side", "N/A")
  entry_date = trade.get("Entry Date", "N/A")
  screenshot = trade.get("Screenshot")

  raw_fin = trade.get("Finalized")
  is_finalized = str(raw_fin).strip().lower() in ("true", "1", "yes")

  sub_actions = df[df["Parent Trade ID"] == trade_id]
  raw_net = trade.get("Net P/L")
  if _has_value(raw_net):
    pnl = to_float(raw_net)
  else:
    pnl = calculate_net_pnl(trade, sub_actions) or 0.0

  state_key = f"mode_{trade_id}"
  current_mode = st.session_state.get(state_key, None)

  current_scale = st.session_state.get("ui_scale", "medium")
  st.markdown(get_card_css(current_scale), unsafe_allow_html=True)

  if is_finalized:
    pnl_color = GREEN if pnl > 0 else (RED if pnl < 0 else GRAY)
    status_indicator = f"<span style='color:{pnl_color}; font-weight:600;'>{pnl:+.2f}$</span>"
  else:
    status_indicator = f"<span style='background-color: {ORANGE}; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight: 500;'>მიმდინარე</span>"
      
  img_url = _get_image_url(screenshot)
  if img_url:
    thumb_html = f"<img src='{img_url}' class='trade-thumb-img'>"
  else:
    thumb_html = "<div class='trade-thumb-placeholder'>📁</div>"
    
  col_thumb, col_info, col_menu = st.columns([0.7, 8.8, 0.5], vertical_alignment="center")

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
        unsafe_allow_html=True
    )

  with col_menu:
    with st.popover("⋯"):
      if st.button("დეტალები", key=f"det_menu_{trade_id}", use_container_width=True):
        show_trade_details_dialog(trade, df)
      
      if st.button("წაშლა", key=f"del_menu_{trade_id}", use_container_width=True):
        st.session_state[state_key] = "delete"
        st.rerun()

  if current_mode == "delete":
    st.error("⚠️ ნამდვილად გსურთ გარიგების წაშლა?")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
      if st.button("დიახ", key=f"conf_del_{trade_id}", use_container_width=True):
        if delete_trade(trade_id):
          st.success("წაიშალა!")
          del st.session_state[state_key]
          st.rerun()
    with col_d2:
      if st.button("გაუქმება", key=f"canc_del_{trade_id}", use_container_width=True):
        del st.session_state[state_key]
        st.rerun()
