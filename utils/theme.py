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
  """Traders Lab ბრენდული ფერების ინექცია თემების მიხედვით."""
  if theme_mode in ("dark", "auto"):
    css = """
        <style>
            [data-testid="stAppViewContainer"], .stApp {
                background-color: #0A0E17 !important;
                color: #FFFFFF !important;
            }
            [data-testid="stHeader"] {
                background-color: rgba(10, 14, 23, 0.85) !important;
            }
            [data-testid="stSidebar"] {
                background-color: #121926 !important;
                border-right: 1px solid rgba(0, 240, 255, 0.12) !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"],
            div[data-testid="stExpander"],
            div.stForm,
            div[data-testid="stDialog"] > div {
                background-color: #121926 !important;
                border: 1px solid rgba(0, 240, 255, 0.18) !important;
                border-radius: 10px !important;
            }
            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #121926 !important;
                color: #FFFFFF !important;
                border-color: #00F0FF !important;
            }
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, [data-testid="stMetricValue"] {
                color: #FFFFFF !important;
            }
            .stCaption, [data-testid="stMetricLabel"] {
                color: #94A3B8 !important;
            }
            a {
                color: #00F0FF !important;
            }
            .stButton button[kind="primary"] {
                background-color: #00F0FF !important;
                color: #0A0E17 !important;
                border: none !important;
                font-weight: 700 !important;
            }
            .stButton button[kind="secondary"] {
                background-color: #1A2333 !important;
                color: #FFFFFF !important;
                border: 1px solid rgba(0, 240, 255, 0.25) !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  else:
    css = """
        <style>
            [data-testid="stAppViewContainer"], .stApp {
                background-color: #F4F7FA !important;
                color: #0A0E17 !important;
            }
            [data-testid="stHeader"] {
                background-color: rgba(244, 247, 250, 0.9) !important;
            }
            [data-testid="stSidebar"] {
                background-color: #E6ECF2 !important;
                border-right: 1px solid #CBD5E1 !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"],
            div[data-testid="stExpander"],
            div.stForm {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
                border-radius: 10px !important;
            }
            h1, h2, h3, h4, h5, h6, p, label, span, .stMarkdown, [data-testid="stMetricValue"] {
                color: #0A0E17 !important;
            }
            .stCaption, [data-testid="stMetricLabel"] {
                color: #475569 !important;
            }
            input, textarea, [data-baseweb="select"] > div {
                background-color: #FFFFFF !important;
                color: #0A0E17 !important;
                border-color: #CBD5E1 !important;
            }
            .stButton button {
                background-color: #FFFFFF !important;
                color: #0A0E17 !important;
                border: 1px solid #CBD5E1 !important;
            }
            .stButton button[kind="primary"] {
                background-color: #0A0E17 !important;
                color: #00F0FF !important;
                border: none !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
