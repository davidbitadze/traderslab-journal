import html
import streamlit as st
from database import delete_trade, thumb_url
from views.trade_dialogs import show_trade_details_dialog, EDIT_STATE_KEY
from utils.formulas import calculate_net_pnl, to_float
from utils.dates import format_display_datetime

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"
ORANGE = "#f97316"

_CARD_CSS = """
<style>
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
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) {
    flex-wrap: nowrap !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) > div:first-child {
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) > div:nth-child(2) {
    flex: 1 1 0 !important;
    width: auto !important;
    min-width: 0 !important;
}
[data-testid="stHorizontalBlock"]:has(.trade-row-marker) > div:last-child {
    display: flex !important;
    justify-content: flex-end !important;
    margin-left: auto !important;
    flex: 0 0 auto !important;
    width: auto !important;
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
  st.markdown(
      get_card_css(st.session_state.get("ui_scale", "medium")),
      unsafe_allow_html=True,
  )

def _has_value(val):
  return val is not None and str(val).strip() not in ("", "None", "nan", "NaT", "<NA>", "No Screenshot")

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

def _side_label(side):
  s = str(side).strip().lower()
  if s == "long":
    return "Long"
  if s == "short":
    return "Short"
  return str(side)

def render_trade_card(trade, df, subs=None, pnl=None):
  trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
  pair = html.escape(str(trade.get("Pair", "N/A")))
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
    status_indicator = f"<span style='color:{pnl_color}; font-weight:600;'>{pnl:+.2f}$</span>"
  else:
    status_indicator = f"<span style='background-color: {ORANGE}; color: white; font-size: 0.6rem; padding: 1px 4px; border-radius: 3px; font-weight: 500;'>მიმდინარე</span>"

  img_url = _get_image_url(screenshot)
  if img_url:
    thumb_html = f"<img src='{html.escape(str(thumb_url(img_url)), quote=True)}' class='trade-thumb-img' loading='lazy' decoding='async'>"
  else:
    thumb_html = "<div class='trade-thumb-placeholder'>📁</div>"

  col_thumb, col_info, col_menu = st.columns([0.7, 8.8, 0.5], vertical_alignment="center")

  with col_thumb:
    st.markdown(thumb_html, unsafe_allow_html=True)

  with col_info:
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
                <span>{format_display_datetime(entry_date) if _has_value(entry_date) else ''}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

  with col_menu:
    with st.popover("⋯"):
      if st.button("დეტალები", key=f"det_menu_{trade_id}", use_container_width=True):
        st.session_state.pop(EDIT_STATE_KEY, None)
        show_trade_details_dialog(trade)

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
