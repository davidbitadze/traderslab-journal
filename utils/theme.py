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

            /* --- 1. ღილაკები ("Add New Trade"): ნაგულისხმევად თეთრი ტექსტი --- */
            .stButton button, .stButton button p, .stButton button span {
                color: #FFFFFF !important;
            }
            /* ჰოვერის დროს ღილაკზე: ფონი ღიავდება, ტექსტი ხდება მუქი (#0A0E17) */
            .stButton button:hover, .stButton button:hover p, .stButton button:hover span {
                color: #0A0E17 !important;
                background-color: #E2E8F0 !important;
            }

            /* --- 2. გარიგების წყვილების სახელები (AUDUSD, EURJPY და ა.შ.): მკაცრად მუქი ფერი (#0A0E17) --- */
            div[data-testid="stHorizontalBlock"] div[data-testid="stMarkdownContainer"] p strong,
            div[data-testid="stVerticalBlock"] div[data-testid="stMarkdownContainer"] p strong,
            .element-container p strong {
                color: #0A0E17 !important;
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
