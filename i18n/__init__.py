"""ენების მოდული: i18n/ საქაღალდეში ყველა <კოდი>.py ფაილი ავტომატურად ხდება ენა.

ფაილს უნდა ჰქონდეს CODE, NAME, FLAG და STRINGS. ბაზისური ენა ka-ა: სხვა ენაში გამოტოვებული
გასაღები მისგან აიღება (და არა ეკრანზე გასაღების სახელი)."""

import importlib
import pkgutil

BASE_LANG = "ka"


def _discover():
  found = {}
  for info in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{__name__}.{info.name}")
    code = getattr(module, "CODE", None)
    strings = getattr(module, "STRINGS", None)
    if code and isinstance(strings, dict):
      found[code] = {
          "name": getattr(module, "NAME", code),
          "flag": getattr(module, "FLAG", ""),
          "strings": strings,
      }
  return found


_LANGS = _discover()
TRANSLATIONS = {code: meta["strings"] for code, meta in _LANGS.items()}


def available_languages():
  """[(კოდი, 'დროშა სახელი'), ...] ბაზისური ენა პირველია."""
  codes = sorted(_LANGS, key=lambda c: (c != BASE_LANG, c))
  return [(c, f"{_LANGS[c]['flag']} {_LANGS[c]['name']}".strip()) for c in codes]


def normalize_lang(code):
  """უცნობ ან ცარიელ კოდს ბაზისურ ენად აქცევს."""
  return code if code in _LANGS else BASE_LANG


def t(key, lang=BASE_LANG, **fmt):
  """აბრუნებს ტექსტს არჩეული ენით; გამოტოვებულია -> ბაზისურ ენაზე; მაშინაც არა -> გასაღები."""
  lang = normalize_lang(lang)
  text = TRANSLATIONS[lang].get(key)
  if text is None:
    text = TRANSLATIONS.get(BASE_LANG, {}).get(key, key)
  if fmt and isinstance(text, str):
    try:
      return text.format(**fmt)
    except (KeyError, IndexError):
      return text
  return text


def missing_keys():
  """{ენა: [გასაღებები, რომლებიც ბაზისურშია, მაგრამ ამ ენაში არა]} - ახალი ენის შესამოწმებლად."""
  base = set(TRANSLATIONS.get(BASE_LANG, {}))
  return {c: sorted(base - set(s)) for c, s in TRANSLATIONS.items() if c != BASE_LANG and base - set(s)}
