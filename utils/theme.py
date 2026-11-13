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
            [data-testid="stAppViewContainer"], .stApp { 
                background-color: #F8FAFC !important; 
                color: #0F172A !important; 
            }
            [data-testid="stSidebar"] { 
                background-color: #E2E8F0 !important; 
            }

            /* 1. ყველა ღილაკი და Popover ("+ Add New Trade", Logout, "...") -> თეთრი ტექსტი */
            .stButton button, .stButton button *,
            [data-testid="stPopover"] button, [data-testid="stPopover"] button *,
            div[data-baseweb="select"] > div, div[data-baseweb="select"] span {
                color: #FFFFFF !important;
            }
            .stButton button:hover, [data-testid="stPopover"] button:hover {
                background-color: #1A2333 !important;
                border-color: #00F0FF !important;
            }
            .stButton button:hover *, [data-testid="stPopover"] button:hover * {
                color: #00F0FF !important;
            }

            /* 2. ზოგადი ტექსტები (საიდბარი და მთავარი გვერდი) -> მუქი ფერი */
            h1, h2, h3, h4, h5, h6, p, label, .stMarkdown,
            [data-testid="stSidebar"] div, [data-testid="stSidebar"] span {
                color: #0F172A !important;
            }

            /* 3. HTML-ში ხელით გაწერილი თეთრი ფერის გადაწერა (AUDUSD, EURJPY და სხვ.) */
            [data-testid="stMarkdownContainer"] div[style*="color"],
            [data-testid="stMarkdownContainer"] span[style*="color: #fff"],
            [data-testid="stMarkdownContainer"] span[style*="color: #FFF"],
            [data-testid="stMarkdownContainer"] span[style*="color: white"] {
                color: #0F172A !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  elif theme_mode in ("dark", "auto"):
    css = """
        <style>
            [data-testid="stAppViewContainer"], .stApp { background-color: #0A0E17 !important; color: #FFFFFF !important; }
            [data-testid="stSidebar"] { background-color: #121926 !important; }
            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #121926 !important;
                color: #FFFFFF !important;
                border-color: rgba(0, 240, 255, 0.2) !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
