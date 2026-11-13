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
  """თემის CSS სტილების ინექცია და ფერების ცენტრალიზებული მართვა მოდალების ჩათვლით."""
  if theme_mode == "light":
    css = """
        <style>
            [data-testid="stAppViewContainer"], .stApp { 
                background-color: #F8FAFC !important; 
                color: #0F172A !important; 
            }
            [data-testid="stSidebar"] { 
                background-color: #E2E8F0 !important; 
                border-right: 1px solid #CBD5E1 !important;
            }

            /* Streamlit მოდალური ფანჯრები და დიალოგები ღია თემაზე */
            div[data-testid="stModal"], div[aria-modal="true"] {
                background-color: rgba(15, 23, 42, 0.2) !important;
            }
            div[data-testid="stModal"] > div, div[aria-modal="true"] > div {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }
            
            /* მოდალის შიგნით არსებული კონტეინერები და ბარათები */
            div[data-testid="stModal"] [data-testid="stVerticalBlock"] > div,
            div[data-testid="stModal"] [data-testid="stContainer"] {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }

            div[data-testid="stModal"] h1, 
            div[data-testid="stModal"] h2, 
            div[data-testid="stModal"] h3, 
            div[data-testid="stModal"] h4,
            div[data-testid="stModal"] p, 
            div[data-testid="stModal"] label,
            div[data-testid="stModal"] span {
                color: #0F172A !important;
            }
            
            div[data-testid="stModal"] input, 
            div[data-testid="stModal"] textarea,
            div[data-testid="stModal"] select {
                background-color: #F8FAFC !important;
                color: #0F172A !important;
                border-color: #CBD5E1 !important;
            }

            /* ზოგადი სათაურები და მთავარი ტექსტები */
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown,
            [data-testid="stSidebar"] div, [data-testid="stSidebar"] span {
                color: #0F172A !important;
            }

            /* გარიგებების ბარათების ტექსტები თემიდან */
            .trade-main-text {
                color: #0F172A !important;
            }
            .trade-sub-text {
                color: #64748B !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  elif theme_mode in ("dark", "auto"):
    css = """
        <style>
            [data-testid="stAppViewContainer"], .stApp { 
                background-color: #0A0E17 !important; 
                color: #FFFFFF !important; 
            }
            [data-testid="stSidebar"] { 
                background-color: #121926 !important; 
                border-right: 1px solid rgba(0, 240, 255, 0.12) !important;
            }

            /* Streamlit მოდალური ფანჯრები მუქ თემაზე */
            div[data-testid="stModal"] > div, div[aria-modal="true"] > div {
                background-color: #0E1117 !important;
                color: #FFFFFF !important;
            }
            
            /* გარიგებების ბარათების ტექსტები მუქ თემაზე */
            .trade-main-text {
                color: #FFFFFF !important;
            }
            .trade-sub-text {
                color: #94A3B8 !important;
            }

            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #121926 !important;
                color: #FFFFFF !important;
                border-color: rgba(0, 240, 255, 0.2) !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
