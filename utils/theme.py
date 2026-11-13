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

            /* --- მონიშნული ღილაკები, სელექტორები და მენეჯმენტ ელემენტები Light რეჟიმში --- */
            
            /* 1. ყველა სტანდარტული ღილაკი და Action ღილაკები (მაგ: Add New Trade, Logout) */
            .stButton button, button[kind="secondary"] {
                background-color: #121926 !important; /* <--- აქ შეგიძლია შეცვალო ფონი */
                color: #FFFFFF !important;             /* <--- აქ შეგიძლია შეცვალო ტექსტის ფერი (#FFFFFF) */
                border: 1px solid #00F0FF !important;
            }
            .stButton button:hover {
                background-color: #1A2333 !important;
                color: #00F0FF !important;
            }

            /* 2. სელექტორები (Language, Theme, Navigation მენიუები სადღაც მარცხნივ/მარჯვნივ) */
            div[data-baseweb="select"] > div {
                background-color: #121926 !important; /* <--- სელექტორის ფონი */
                color: #FFFFFF !important;             /* <--- სელექტორის ტექსტის ფერი */
                border-color: #00F0FF !important;
            }
            div[data-baseweb="select"] span {
                color: #FFFFFF !important;
            }

            /* 3. მარჯვენა სამწერტილიანი მენიუს ღილაკები და ბალანსის ბეჯი */
            [data-testid="stMetric"], .stMetric {
                background-color: #121926 !important;
                color: #FFFFFF !important;
                padding: 6px 12px;
                border-radius: 6px;
            }
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
