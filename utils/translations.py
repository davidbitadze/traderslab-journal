"""თავსებადობისთვის: ძველი `from utils.translations import t` ისევ მუშაობს. თარგმანები i18n/ საქაღალდეშია."""

from i18n import TRANSLATIONS, available_languages, missing_keys, normalize_lang, t  # noqa: F401
