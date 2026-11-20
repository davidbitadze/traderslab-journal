"""ვიზუალური მხარე: მასშტაბი, თემა, მობილურის ამოცნობა."""

import html
from pathlib import Path

import streamlit as st

_ASSETS = Path(__file__).resolve().parent.parent / "assets"


@st.cache_resource
def _read_css(name):
  text = (_ASSETS / f"theme_{name}.css").read_text(encoding="utf-8")
  # ცარიელი ხაზები markdown-ის HTML ბლოკს ამთავრებს: ვხსნით
  return "\n".join(line for line in text.splitlines() if line.strip())


def detect_is_mobile():
  """ამოწმებს ბრაუზერის User-Agent-ს მობილურის დასადგენად."""
  try:
    headers = getattr(st.context, "headers", {})
    user_agent = headers.get("User-Agent", "").lower()
    mobile_keywords = ["android", "iphone", "ipad", "ipod", "mobile", "tablet"]
    return any(kw in user_agent for kw in mobile_keywords)
  except Exception:
    return False


def apply_ui_scaling(scale_mode):
  """ადგენს CSS სტილებს არჩეული მასშტაბის მიხედვით."""
  styles = {
      "small": """
            <style>
                html, body, [class*="css"] { font-size: 13px !important; }
                .stButton button { padding: 0.25rem 0.5rem !important; font-size: 12px !important; }
            </style>
        """,
      "medium": """
            <style>
                html, body, [class*="css"] { font-size: 15px !important; }
            </style>
        """,
      "large": """
            <style>
                html, body, [class*="css"] { font-size: 17px !important; }
            </style>
        """,
  }
  st.markdown(styles.get(scale_mode, styles["medium"]), unsafe_allow_html=True)


def apply_theme_styles(theme_mode):
  """თემის CSS (assets/theme_light.css და theme_dark.css) ერთხელ იკითხება და ქეშირდება."""
  name = "light" if theme_mode == "light" else "dark"  # "auto" მუქ ბაზასთან ერთად მუშაობს
  st.markdown(f"<style>{_read_css(name)}</style>", unsafe_allow_html=True)


def show_table(table, pnl_cols=()):
  """ცხრილი თემის მიხედვით.

  მუქ თემაზე — ჩვეულებრივი st.dataframe. ღია თემაზე st.dataframe canvas-ზე იხატება და CSS-ით
  ვერ იცვლება, ამიტომ იქ ჩვეულებრივი HTML ცხრილი გამოდის (ფერები theme_light.css-ის გარეშეც სწორია).
  """
  pnl_cols = list(pnl_cols or [])
  if st.session_state.get("theme", "auto") != "light":
    styler = table.style
    if pnl_cols:
      styler = styler.format({c: "{:+.2f}" for c in pnl_cols})
      fn = styler.map if hasattr(styler, "map") else styler.applymap
      styler = fn(
          lambda v: ("color: #22C55E; font-weight: 600" if v > 0 else "color: #EF4444; font-weight: 600" if v < 0 else "")
          if isinstance(v, (int, float)) else "",
          subset=pnl_cols,
      )
    st.dataframe(styler, use_container_width=True, hide_index=True)
    return

  th = "padding:8px 10px;text-align:left;background:#F1F5F9;color:#0F172A;border-bottom:1px solid #CBD5E1;font-weight:600;"
  head = "".join(f"<th style=\"{th}\">{html.escape(str(c))}</th>" for c in table.columns)
  rows = []
  for _, row in table.iterrows():
    cells = []
    for c in table.columns:
      v = row[c]
      color, weight, align = "#0F172A", "400", "left"
      if isinstance(v, (int, float)) and not isinstance(v, bool):
        align = "right"
        text = f"{v:+.2f}" if c in pnl_cols else (f"{v:g}" if float(v).is_integer() or abs(v) >= 1000 else f"{v:.2f}")
        if c in pnl_cols and v != 0:
          color, weight = ("#15803D" if v > 0 else "#B91C1C"), "600"
      else:
        text = "—" if v is None or (isinstance(v, float) and v != v) else str(v)
      cells.append(
          f"<td style=\"padding:7px 10px;text-align:{align};color:{color};font-weight:{weight};"
          f"border-bottom:1px solid #E2E8F0;\">{html.escape(text)}</td>"
      )
    rows.append("<tr>" + "".join(cells) + "</tr>")
  st.markdown(
      "<div style=\"overflow-x:auto;background:#FFFFFF;border:1px solid #CBD5E1;border-radius:8px;\">"
      "<table style=\"width:100%;border-collapse:collapse;font-size:14px;\">"
      f"<thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>",
      unsafe_allow_html=True,
  )
