"""ვიზუალური მხარე: მასშტაბი, თემა, მობილურის ამოცნობა."""

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
