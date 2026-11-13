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

            /* 1. ღილაკები და პოპოვერები -> თეთრი ტექსტი */
            .stButton button, .stButton button *,
            [data-testid="stPopover"] button, [data-testid="stPopover"] button * {
                color: #FFFFFF !important;
            }
            .stButton button:hover, [data-testid="stPopover"] button:hover {
                background-color: #E2E8F0 !important;
            }
            .stButton button:hover *, [data-testid="stPopover"] button:hover * {
                color: #0A0E17 !important;
            }

            /* 2. საიდბარი */
            [data-testid="stSidebar"] label, 
            [data-testid="stSidebar"] .stMarkdown p,
            [data-testid="stSidebar"] span {
                color: #0F172A !important;
            }

            /* 3. მთავარი გვერდი და გარიგებების ბარათები (მათ შორის AUDUSD, EURJPY და ა.შ.) */
            div[data-testid="stMain"] p,
            div[data-testid="stMain"] span,
            div[data-testid="stMain"] strong,
            div[data-testid="stMain"] div {
                color: #0F172A;
            }
            
            /* PnL ფერები რომ არ გაფუჭდეს (+25.49$ და -10.51$) */
            div[data-testid="stMain"] span[style*="color: #4CAF50"],
            div[data-testid="stMain"] span[style*="color: rgb"],
            div[data-testid="stMain"] font {
                /* ვტოვებთ დინამიკურ ფერებს */
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
  elif theme_mode == "dark":
    # მუქი თემის სტილები...
    pass
