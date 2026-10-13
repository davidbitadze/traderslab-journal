# utils/translations.py

TRANSLATIONS = {
    "ka": {
        "page_title": "Traders Lab - სავაჭრო ჟურნალი",
        "nav_header": "🧭 ნავიგაცია",
        "menu_journal": "📊 სავაჭრო ჟურნალი",
        "menu_add": "➕ ახალი გარიგება",
        "menu_analytics": "📈 ანალიტიკა",
        "lang_select": "ენა / Language",
        "journal_title": "📊 არსებული გარიგებების ისტორია",
        "empty_table": "ცხრილი ამჟამად ცარიელია.",
        "add_title": "➕ ახალი გარიგების დამატება",
        "pair": "ვალუტის წყვილი (Pair)",
        "entry_price": "შესვლის ფასი (Entry Price)",
        "qty": "მოცულობა (Qty)",
        "side": "მიმართულება (Side)",
        "pattern": "პატერნი",
        "trigger": "ტრიგერი",
        "save_btn": "გარიგების შენახვა ბაზაში",
        "success_save": "გარიგება წარმატებით შეინახა ბაზაში!",
        "analytics_title": "📈 სტატისტიკა და ანალიტიკა",
        "total_trades": "სულ გარიგებები",
    },
    "en": {
        "page_title": "Traders Lab - Trading Journal",
        "nav_header": "🧭 Navigation",
        "menu_journal": "📊 Trading Journal",
        "menu_add": "➕ New Trade",
        "menu_analytics": "📈 Analytics",
        "lang_select": "Language / ენა",
        "journal_title": "📊 Existing Trades History",
        "empty_table": "The table is currently empty.",
        "add_title": "➕ Add New Trade",
        "pair": "Currency Pair",
        "entry_price": "Entry Price",
        "qty": "Quantity (Qty)",
        "side": "Side",
        "pattern": "Pattern",
        "trigger": "Trigger",
        "save_btn": "Save Trade to Database",
        "success_save": "Trade successfully saved to database!",
        "analytics_title": "📈 Statistics & Analytics",
        "total_trades": "Total Trades",
    },
}


def t(key, lang="ka"):
  """მთავარი ფუნქცია ტექსტების გამოსაძახებლად არჩეული ენის მიხედვით"""
  return TRANSLATIONS.get(lang, TRANSLATIONS["ka"]).get(key, key)
