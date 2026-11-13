import streamlit as st


def apply_theme_styles(theme_mode):
  """Traders Lab ბრენდული ფერების ინექცია თემების მიხედვით."""
  
  # თუ არჩეულია ბნელი თემა ან Auto (რომელიც ნაგულისხმევად ბნელია Traders Lab-ისთვის)
  if theme_mode == "dark" or theme_mode == "auto":
    css = """
        <style>
            /* მთლიანი აპლიკაციის ფონი */
            [data-testid="stAppViewContainer"] {
                background-color: #0A0E17 !important;
                color: #FFFFFF !important;
            }
            /* გვერდითა მენიუს (Sidebar) ფონი */
            [data-testid="stSidebar"] {
                background-color: #121926 !important;
                color: #FFFFFF !important;
            }
            /* კონტეინერების და ბარათების ფონი */
            div[data-testid="stVerticalBlock"] > div[data-testid="stContainer"],
            div[data-testid="stExpander"], 
            div.stForm {
                background-color: #121926 !important;
                border: 1px solid rgba(0, 240, 255, 0.15) !important;
                border-radius: 8px !important;
            }
            /* შეტყობინებები და ალერტები */
            div[data-baseweb="notification"], .stAlert, div.stInfo, div.stSuccess {
                background-color: #121926 !important;
                color: #FFFFFF !important;
                border-color: #00F0FF !important;
            }
            /* ტექსტების და სათაურების ფერი */
            h1, h2, h3, h4, h5, h6, span, p, label {
                color: #FFFFFF !important;
            }
            /* ღილაკები და აქცენტები */
            .stButton button[kind="primary"] {
                background-color: #00F0FF !important;
                color: #0A0E17 !important;
                font-weight: 600 !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
  else:
    # Light თემის შემთხვევაშიც ვიყენებთ Traders Lab-ის რბილ ღია/ნაცრისფერ ტონებს, რომ არ აჭრელდეს
    css = """
        <style>
            [data-testid="stAppViewContainer"] {
                background-color: #f8f9fa !important;
                color: #0A0E17 !important;
            }
            [data-testid="stSidebar"] {
                background-color: #e9ecef !important;
                color: #0A0E17 !important;
            }
            div[data-testid="stExpander"], div.stForm {
                background-color: #ffffff !important;
                border: 1px solid #cbd5e1 !important;
            }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)
