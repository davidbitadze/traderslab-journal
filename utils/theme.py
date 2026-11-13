"""ვიზუალური მხარე: მასშტაბი, თემა, მობილურის ამოცნობა."""

import streamlit as st


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
  """თემის CSS სტილების ინექცია."""
  if theme_mode == "light":
    css = """
        <style>
            [data-testid="stAppViewContainer"] { background-color: #f8f9fa; color: #212529; }
            [data-testid="stSidebar"] { background-color: #e9ecef; }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  elif theme_mode == "dark":
    css = """
        <style>
            [data-testid="stAppViewContainer"] { background-color: #0e1117; color: #fafafa; }
            [data-testid="stSidebar"] { background-color: #1a1c23; color: #fafafa; }
            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #1a1c23 !important;
                color: #fafafa !important;
                border-color: #333333 !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
