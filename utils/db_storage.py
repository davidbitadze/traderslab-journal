import io
import uuid
import streamlit as st
from i18n import t
from utils.db_core import get_data_client, _uid

SCREENSHOT_BUCKET = "screenshots"
MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # ატვირთული ფაილის მაქსიმალური ზომა (დამუშავებამდე)
MAX_IMAGE_PIXELS = 40_000_000  # "დეკომპრესიული ბომბისგან" დასაცავად
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP"}
FULL_MAX_SIDE = 1600  # სრული სურათის მაქს. გვერდი (px)
FULL_QUALITY = 80
THUMB_MAX_SIDE = 360  # სიის პატარა პრევიუ
THUMB_QUALITY = 70
_PUBLIC_MARKER = f"/object/public/{SCREENSHOT_BUCKET}/"


def _prepare_images(raw):
  """აბრუნებს (სრული WebP, პატარა პრევიუ WebP) ბაიტებს, ან None თუ სურათი ვერ დამუშავდა."""
  try:
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    opened = Image.open(io.BytesIO(raw))
    if opened.format not in ALLOWED_FORMATS:
      return None
    img = ImageOps.exif_transpose(opened)
    if img.mode in ("RGBA", "LA", "P"):
      img = img.convert("RGBA")
      background = Image.new("RGB", img.size, (255, 255, 255))
      background.paste(img, mask=img.split()[-1])
      img = background
    elif img.mode != "RGB":
      img = img.convert("RGB")

    full = img.copy()
    full.thumbnail((FULL_MAX_SIDE, FULL_MAX_SIDE))
    out = io.BytesIO()
    full.save(out, format="WEBP", quality=FULL_QUALITY, method=4)
    full_bytes = out.getvalue()

    thumb = img.copy()
    thumb.thumbnail((THUMB_MAX_SIDE, THUMB_MAX_SIDE))
    out = io.BytesIO()
    thumb.save(out, format="WEBP", quality=THUMB_QUALITY, method=4)
    return full_bytes, out.getvalue()
  except Exception:
    return None


def _storage_path(url):
  """საჯარო ბმულიდან ობიექტის გზა bucket-ში (ან None)."""
  text = str(url or "")
  idx = text.find(_PUBLIC_MARKER)
  if idx < 0:
    return None
  return text[idx + len(_PUBLIC_MARKER) :].split("?")[0] or None


def _is_managed_path(path):
  return bool(path) and "/" in path and path.endswith(".webp")


def thumb_url(url):
  """სიისთვის პატარა პრევიუს ბმული; ძველი სურათებისთვის იგივე ბმული."""
  path = _storage_path(url)
  if _is_managed_path(path):
    return str(url).split("?")[0][: -len(".webp")] + "_t.webp"
  return url


def delete_screenshot(url):
  """სურათს (და მის პრევიუს) შლის Storage-იდან."""
  path = _storage_path(url)
  if not _is_managed_path(path):
    return False
  try:
    get_data_client().storage.from_(SCREENSHOT_BUCKET).remove(
        [path, path[: -len(".webp")] + "_t.webp"]
    )
    return True
  except Exception:
    return False


def upload_screenshot(uploaded_file, file_name=None, lang=None):
  """სურათს ოპტიმიზაციის შემდეგ ტვირთავს <user_id>/ საქაღალდეში (+ პატარა პრევიუ).

  მხოლოდ ნამდვილი PNG/JPG/WEBP მიიღება: რასაც Pillow ვერ ხსნის, ის არ ინახება (საჯარო bucket-ში
  თვითნებური ფაილი, მაგ. HTML, არ უნდა აღმოჩნდეს)."""
  lang = lang or st.session_state.get("lang", "ka")
  try:
    raw = uploaded_file.getvalue()
    if len(raw) > MAX_UPLOAD_BYTES:
      st.error(t("upload_too_large", lang, mb=MAX_UPLOAD_BYTES // (1024 * 1024)))
      return None
    prepared = _prepare_images(raw)
    if not prepared:
      st.error(t("upload_invalid", lang))
      return None

    supabase = get_data_client()
    folder = _uid() or "anon"
    token = uuid.uuid4().hex
    bucket = supabase.storage.from_(SCREENSHOT_BUCKET)
    options = {"upsert": "false", "cache-control": "31536000", "content-type": "image/webp"}

    full_bytes, thumb_bytes = prepared
    path = f"{folder}/{token}.webp"
    bucket.upload(path, full_bytes, options)
    try:
      bucket.upload(f"{folder}/{token}_t.webp", thumb_bytes, options)
    except Exception:
      bucket.remove([path])
      raise
    return bucket.get_public_url(path)
  except Exception as e:
    print(f"upload_screenshot error: {e!r}")  # დეტალი მხოლოდ სერვერის ლოგში
    st.error(t("db_generic_error", lang))
    return None
