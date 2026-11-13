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

            /* Streamlit პოპოვერები (Add New Trade მენიუ) */
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

            /* "გარიგების წაშლა" და სხვა მუქი ღილაკები მოდალში/ინტერფეისში */
            div[data-testid="stDialog"] .stButton button, 
            div[data-testid="stModal"] .stButton button {
                background-color: #1E293B !important;
                color: #FFFFFF !important;
                border: 1px solid #334155 !important;
            }
            div[data-testid="stDialog"] .stButton button *, 
            div[data-testid="stModal"] .stButton button * {
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


            /* ღილაკები გვერდით მენიუშიც: ტექსტი თეთრი რჩება (ზოგადი div წესს არ ემორჩილება) */
            [data-testid="stSidebar"] .stButton button, [data-testid="stSidebar"] .stButton button * {
                color: #FFFFFF !important;
            }

            /* ინფუთები მთავარ გვერდზეც */
            [data-testid="stAppViewContainer"] input, [data-testid="stAppViewContainer"] textarea,
            [data-baseweb="select"] > div, [data-baseweb="input"] {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
                border-color: #CBD5E1 !important;
            }
            [data-baseweb="popover"] ul, [data-baseweb="menu"] {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }

            /* ტაბები, მეტრიკები, ბარათები */
            [data-baseweb="tab"] { color: #334155 !important; }
            [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #0F172A !important; }
            [data-testid="stCaptionContainer"] { color: #64748B !important; }
            [data-testid="stVerticalBlockBorderWrapper"] { border-color: #CBD5E1 !important; }

            /* შეტყობინებები (info/success/warning/error) */
            [data-testid="stAlert"], div[data-baseweb="notification"] {
                background-color: #EFF6FF !important;
                border: 1px solid #BFDBFE !important;
            }
            [data-testid="stAlert"] * { color: #0F172A !important; }


            /* ფორმის ღილაკები (გაუქმება, დამატება...) - st.form_submit_button .stButton კლასს არ ატარებს */
            [data-testid="stBaseButton-secondaryFormSubmit"],
            [data-testid="stBaseButton-secondary"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
            }
            [data-testid="stFormSubmitButton"] button *, [data-testid="stBaseButton-secondaryFormSubmit"] *,
            [data-testid="stBaseButton-secondary"] *, [data-testid="stBaseButton-primary"] *,
            [data-testid="stBaseButton-primaryFormSubmit"] * {
                color: #FFFFFF !important;
            }

            /* ფაილის ასატვირთი (სკრინშოტი): ღია ფონი და მუქი ტექსტი */
            [data-testid="stFileUploaderDropzone"] {
                background-color: #F1F5F9 !important;
                border: 1px dashed #94A3B8 !important;
            }
            [data-testid="stFileUploaderDropzone"] span, [data-testid="stFileUploaderDropzone"] small,
            [data-testid="stFileUploaderDropzone"] div, [data-testid="stFileUploaderDropzoneInstructions"] * {
                color: #475569 !important;
            }
            [data-testid="stFileUploaderDropzone"] button {
                background-color: #FFFFFF !important;
                border: 1px solid #CBD5E1 !important;
            }
            [data-testid="stFileUploaderDropzone"] button * { color: #0F172A !important; }
            [data-testid="stFileUploaderFile"] * { color: #0F172A !important; }


            /* დიალოგებში/პოპოვერში ღილაკების ტექსტი თეთრია (ზოგადი p/span წესზე უფრო მკაცრი სელექტორი) */
            div[data-testid="stDialog"] button p, div[data-testid="stDialog"] button span, div[data-testid="stDialog"] button div,
            div[data-testid="stModal"] button p, div[data-testid="stModal"] button span, div[data-testid="stModal"] button div,
            [data-testid="stPopoverBody"] button p, [data-testid="stPopoverBody"] button span, [data-testid="stPopoverBody"] button div {
                color: #FFFFFF !important;
            }
            div[data-testid="stDialog"] [data-testid="stFileUploaderDropzone"] button,
            div[data-testid="stModal"] [data-testid="stFileUploaderDropzone"] button,
            [data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzone"] button {
                background-color: #FFFFFF !important;
            }
            div[data-testid="stDialog"] [data-testid="stFileUploaderDropzone"] button *,
            div[data-testid="stModal"] [data-testid="stFileUploaderDropzone"] button *,
            [data-testid="stPopoverBody"] [data-testid="stFileUploaderDropzone"] button * {
                color: #0F172A !important;
            }

            /* შეტყობინებები (Streamlit-ის ახალი სტრუქტურა) */
            [data-testid="stAlertContainer"] {
                background-color: #EFF6FF !important;
                border: 1px solid #BFDBFE !important;
            }
            [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background-color: #F0FDF4 !important; border-color: #BBF7D0 !important; }
            [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background-color: #FFFBEB !important; border-color: #FDE68A !important; }
            [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background-color: #FEF2F2 !important; border-color: #FECACA !important; }
            [data-testid="stAlertContainer"] * { color: #0F172A !important; }

            /* გამორთული ველები (მაგ. თარიღი) */
            input:disabled, textarea:disabled, [data-baseweb="input"]:has(input:disabled), [data-baseweb="base-input"] {
                background-color: #E2E8F0 !important;
                color: #475569 !important;
                -webkit-text-fill-color: #475569 !important;
            }
            [data-testid="stDateInput"] > div, [data-testid="stDateInput"] input, [data-testid="stTimeInput"] input {
                background-color: #FFFFFF !important;
                color: #0F172A !important;
            }


            /* გამორთული თარიღის ველი (Last day UTC): ყველა შიდა ფენა ღია ფონზე, ტექსტი მუქი */
            [data-testid="stDateInput"] div, [data-testid="stDateInput"] input,
            [data-testid="stDateInputField"], [data-testid="stDateInput"] [data-baseweb] {
                background-color: #E2E8F0 !important;
                color: #334155 !important;
                -webkit-text-fill-color: #334155 !important;
                opacity: 1 !important;
            }
            [data-testid="stDateInput"] svg { fill: #334155 !important; color: #334155 !important; }
            [aria-disabled="true"] input, input[disabled] {
                color: #334155 !important;
                -webkit-text-fill-color: #334155 !important;
                opacity: 1 !important;
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
