"""თავსებადობისთვის: ძველი `from utils.translations import t` ისევ მუშაობს. თარგმანები i18n/ საქაღალდეშია."""

from i18n import TRANSLATIONS, available_languages, detect_browser_lang, missing_keys, normalize_lang, t  # noqa: F401
