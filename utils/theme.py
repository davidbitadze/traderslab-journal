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
            /* მთავარი ფონი და ტექსტი */
            [data-testid="stAppViewContainer"], .stApp { 
                background-color: #F8FAFC !important; 
                color: #0F172A !important; 
            }
            [data-testid="stSidebar"] { 
                background-color: #E2E8F0 !important; 
                border-right: 1px solid #CBD5E1 !important;
            }

            /* Streamlit მოდალური ფანჯრები და დიალოგები (სრულად თეთრი ფონი) */
            div[data-testid="stDialog"], div[data-testid="stModal"], div[aria-modal="true"] {
                background-color: rgba(15, 23, 42, 0.25) !important;
            }
            div[data-testid="stDialog"] > div, div[data-testid="stModal"] > div, div[aria-modal="true"] > div {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }
            
            /* მოდალის შიგნით არსებული კონტეინერები და ტექსტები */
            div[data-testid="stDialog"] [data-testid="stVerticalBlock"] > div,
            div[data-testid="stModal"] [data-testid="stVerticalBlock"] > div {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }
            div[data-testid="stDialog"] label, div[data-testid="stModal"] label,
            div[data-testid="stDialog"] p, div[data-testid="stModal"] p,
            div[data-testid="stDialog"] span, div[data-testid="stModal"] span,
            div[data-testid="stDialog"] h1, div[data-testid="stDialog"] h2, div[data-testid="stDialog"] h3,
            div[data-testid="stModal"] h1, div[data-testid="stModal"] h2, div[data-testid="stModal"] h3 {
                color: #0F172A !important;
            }

            /* Streamlit პოპოვერები (Add New Trade მენიუ) - სრულად თეთრი ფონი და მუქი ტექსტები */
            [data-testid="stPopoverBody"] {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
                border: 1px solid #CBD5E1 !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
            }
            [data-testid="stPopoverBody"] label, 
            [data-testid="stPopoverBody"] p, 
            [data-testid="stPopoverBody"] span, 
            [data-testid="stPopoverBody"] h1, 
            [data-testid="stPopoverBody"] h2, 
            [data-testid="stPopoverBody"] h3,
            [data-testid="stPopoverBody"] div {
                color: #0F172A !important;
            }
            [data-testid="stPopoverBody"] input, 
            [data-testid="stPopoverBody"] textarea, 
            [data-testid="stPopoverBody"] select {
                background-color: #F8FAFC !important;
                color: #0F172A !important;
                border: 1px solid #CBD5E1 !important;
            }

            /* ბალანსის ბარათი (ზედა მარჯვენა კუთხეში) - ტექსტი თეთრი */
            div:has(> [data-testid="stMarkdownContainer"] *:contains("Balance")) {
                color: #FFFFFF !important;
            }
            div:has(> [data-testid="stMarkdownContainer"] *:contains("Balance")) * {
                color: #FFFFFF !important;
            }

            /* ინფუთები და ველები დიალოგებში */
            div[data-testid="stDialog"] input, div[data-testid="stDialog"] textarea, div[data-testid="stDialog"] select,
            div[data-testid="stModal"] input, div[data-testid="stModal"] textarea, div[data-testid="stModal"] select {
                background-color: #F8FAFC !important;
                color: #0F172A !important;
                border: 1px solid #CBD5E1 !important;
            }

            /* ზოგადი ღილაკები ჰოვერ ეფექტით */
            .stButton button, button[kind="secondary"], button[kind="primary"] {
                background-color: #1E293B !important;
                color: #FFFFFF !important;
                border: 1px solid #334155 !important;
                transition: all 0.2s ease-in-out;
            }
            .stButton button:hover, button[kind="secondary"]:hover, button[kind="primary"]:hover {
                background-color: #334155 !important;
                border-color: #475569 !important;
                color: #FFFFFF !important;
            }
            .stButton button *, button[kind="secondary"] *, button[kind="primary"] * {
                color: #FFFFFF !important;
            }

            /* ზოგადი სათაურები და ტექსტები გვერდზე */
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown, span,
            [data-testid="stSidebar"] div, [data-testid="stSidebar"] span {
                color: #0F172A !important;
            }

            /* გარიგებების ბარათების ტექსტები */
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
            div[data-testid="stDialog"] > div, div[data-testid="stModal"] > div, div[aria-modal="true"] > div {
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
