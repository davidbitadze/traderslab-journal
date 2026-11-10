TRANSLATIONS = {
    "ka": {
        # ნავიგაცია და ზოგადი
        "nav_header": "ნავიგაცია",
        "journal": "📊 სავაჭრო ჟურნალი",
        "analytics": "📈 ანალიტიკა",
        "settings": "⚙️ პარამეტრები და ცნობარები",
        "admin": "🛡️ ადმინისტრაცია",
        "logout": "🚪 გასვლა (Logout)",
        "language": "Language / ენა",
        "device": "მოწყობილობა",
        "desktop": "💻 დესკტოპი",
        "mobile": "📱 მობილური",
        "scale": "ზომა",
        "credits": "ბალანსი",
        "credit_unit": "ქულა",
        "theme_label": "🎨 თემა (Theme)",
        "theme_dark": "🌙 ბნელი (Dark)",
        "theme_light": "☀️ ღია (Light)",
        "theme_auto": "🔄 სისტემური (Auto)",
        "journal_title": "სავაჭრო ჟურნალი",
        "balance_label": "ბალანსი",
        "credits_label": "ქულა",
        "add_trade_btn": "➕ ახალი გარიგების დამატება",
        "no_trades_msg": "ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.",
        
        # ავტორიზაცია
        "auth_title": "🔐 Traders Lab - ავტორიზაცია",
        "auth_subtitle": "გთხოვთ გაიარეთ ავტორიზაცია სისტემაში შესასვლელად.",
        "tab_login": "შესვლა (Login)",
        "tab_register": "რეგისტრაცია (Register)",
        "email_label": "ელ-ფოსტა (Email)",
        "pass_label": "პაროლი (Password)",
        "remember_me": "მიმახსოვრე (Remember me)",
        "login_btn": "შესვლა",
        "register_btn": "რეგისტრაცია",
        "resend_email": "📧 დადასტურების წერილის ხელახლა გაგზავნა",
        "reg_success": "რეგისტრაცია წარმატებულია! გაგიგზავნეთ წერილი: დააჭირე მასში დადასტურების ბმულს და შემდეგ შედი სისტემაში.",
        "sub_expired_error": "⚠️ **თქვენი გამოწერის ვადა ამოწურულია ან აქტიური არ არის.** სავაჭრო ჟურნალსა და ანალიტიკაზე წვდომისთვის გთხოვთ განაახლოთ გამოწერა.",
        
        # ჟურნალი
        "trade_journal_title": "სავაჭრო ჟურნალი",
        "add_trade_btn": "➕ ახალი გარიგების დამატება",
        "no_trades": "ჟურნალში გარიგებები ჯერ არ არის. გამოიყენეთ ზედა ღილაკი.",
        
        # ადმინ პანელი
        "admin_title": "🛡️ ადმინისტრატორის პანელი",
        "admin_auth_user": "ავტორიზებული ადმინი",
        "admin_no_access": "⛔ თქვენ არ გაქვთ ადმინისტრატორის უფლებები.",
        "users_management": "👥 მომხმარებლების მართვა",
        "credits_topup": "💳 კრედიტების / ქულების ჩარიცხვა",
        "select_user": "აირჩიეთ მომხმარებელი",
        "add_credits_label": "ქულების დამატება (მაგ. 50)",
        "topup_btn": "➕ ქულების ჩარიცხვა",
        "exact_balance_label": "ზუსტი ბალანსის მითითება",
        "update_balance_btn": "✏️ ბალანსის განახლება",
    },
    "en": {
        # Navigation & General
        "nav_header": "Navigation",
        "journal": "📊 Trade Journal",
        "analytics": "📈 Analytics",
        "settings": "⚙️ Settings & References",
        "admin": "🛡️ Administration",
        "logout": "🚪 Logout",
        "language": "Language / ენა",
        "device": "Device",
        "desktop": "💻 Desktop",
        "mobile": "📱 Mobile",
        "scale": "Scale",
        "credits": "Balance",
        "credit_unit": "credits",
        "theme_label": "🎨 Theme",
        "theme_dark": "🌙 Dark",
        "theme_light": "☀️ Light",
        "theme_auto": "🔄 System Auto",
        "journal_title": "Trade Journal",
        "balance_label": "Balance",
        "credits_label": "credits",
        "add_trade_btn": "➕ Add New Trade",
        "no_trades_msg": "No trades in the journal yet. Use the button above.",
        
        # Authorization
        "auth_title": "🔐 Traders Lab - Authorization",
        "auth_subtitle": "Please log in to access the system.",
        "tab_login": "Login",
        "tab_register": "Register",
        "email_label": "Email",
        "pass_label": "Password",
        "remember_me": "Remember me",
        "login_btn": "Log In",
        "register_btn": "Register",
        "resend_email": "📧 Resend confirmation email",
        "reg_success": "Registration successful! We've sent you an email: click the confirmation link and then log into the system.",
        "sub_expired_error": "⚠️ **Your subscription has expired or is not active.** Please renew your subscription to access the trade journal and analytics.",
        
        # Journal
        "trade_journal_title": "Trade Journal",
        "add_trade_btn": "➕ Add New Trade",
        "no_trades": "No trades in the journal yet. Use the button above.",
        
        # Admin Panel
        "admin_title": "🛡️ Administrator Panel",
        "admin_auth_user": "Authorized Admin",
        "admin_no_access": "⛔ You do not have administrator permissions.",
        "users_management": "👥 User Management",
        "credits_topup": "💳 Credits / Top-up",
        "select_user": "Select User",
        "add_credits_label": "Add Credits (e.g., 50)",
        "topup_btn": "➕ Top-up Credits",
        "exact_balance_label": "Set Exact Balance",
        "update_balance_btn": "✏️ Update Balance",
    }
}

def t(key, lang="ka"):
  """აბრუნებს ტექსტს არჩეული ენის მიხედვით."""
  return TRANSLATIONS.get(lang, TRANSLATIONS["ka"]).get(key, key)
