import io
import os
import re
import uuid

import pandas as pd
import streamlit as st
from supabase import create_client

# ქეშის ვადა (წმ). ბაზაში ჩაწერისას ქეში ყოველთვის იწმინდება, ამიტომ TTL
# მხოლოდ იმ შემთხვევისთვისაა, როცა მონაცემი გარედან შეიცვლება (მაგ. Supabase-ის პანელიდან).
TRADES_TTL = 120
SETTINGS_TTL = 600
BALANCE_TTL = 300

# Supabase ერთ მოთხოვნაზე ნაგულისხმევად მაქს. 1000 რიგს აბრუნებს
PAGE_SIZE = 1000

BALANCE_COLUMNS = ["Transaction ID", "Date", "Amount", "Description"]


def _make_client(auth_safe=False):
  url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
  if auth_safe:
    # სესიას თავად ვმართავთ (app-ის cookie): ფონური ტაიმერი და ფაილზე შენახვა გვჭირდება გამორთული
    try:
      from supabase import ClientOptions

      return create_client(
          url,
          key,
          options=ClientOptions(auto_refresh_token=False, persist_session=False),
      )
    except Exception:
      pass
  return create_client(url, key)


def new_auth_client():
  """ერთი მომხმარებლის სესიისთვის ახალი კლიენტი. login-ის შემდეგ მასზე ინახება მისი JWT,
  ამიტომ არასდროს უნდა გავუზიაროთ სხვა სესიას (იხ. utils/auth.py)."""
  return _make_client(auth_safe=True)


# ძველი სახელი, რომ სხვა ფაილებმა არ გატყდეს
get_supabase_client = new_auth_client


@st.cache_resource
def _anon_client():
  return _make_client()


def get_data_client():
  """მონაცემებისთვის: ავტორიზებული მომხმარებლის საკუთარი კლიენტი (მისი JWT-ით, რომ
  ბაზის RLS წესები მუშაობდეს). დალოგინებამდე — უფლებებმოკლებული anon კლიენტი."""
  return st.session_state.get("sb") or _anon_client()


def _uid():
  """ქეშის გასაღებში ვრთავთ user_id-ს, რომ ერთი მომხმარებლის მონაცემი სხვას არ დაუბრუნდეს."""
  user = st.session_state.get("user")
  return getattr(user, "id", None)


# ------------------------------------------------------------------ trades
@st.cache_data(ttl=TRADES_TTL, show_spinner=False)
def _load_trades(uid):
  """ყველა რიგის წამოღება გვერდებად (1000-ზე მეტი რიგიც სწორად წამოვა).
  შეცდომა ქეშში არ ინახება: ის ზევით იჭერს fetch_trades()."""
  client = get_data_client()
  rows, start = [], 0
  while True:
    response = (
        client.table("trades")
        .select("*")
        .order("Entry Date", desc=True)
        .order("Trade ID")
        .range(start, start + PAGE_SIZE - 1)
        .execute()
    )
    data = response.data or []
    rows.extend(data)
    if len(data) < PAGE_SIZE:
      break
    start += PAGE_SIZE
  return pd.DataFrame(rows) if rows else pd.DataFrame()


def invalidate_trades():
  _load_trades.clear()


def fetch_trades():
  try:
    uid = _uid()
    if not uid:
      return pd.DataFrame()
    return _load_trades(uid)
  except Exception as e:
    st.error(f"ბაზიდან მონაცემის წამოღების შეცდომა: {e}")
    return pd.DataFrame()


def insert_trade(trade_data):
  try:
    get_data_client().table("trades").insert(trade_data).execute()
    invalidate_trades()
    return True
  except Exception as e:
    st.error(f"ბაზაში ჩაწერის შეცდომა: {e}")
    return False


def update_trade(trade_id, updated_data):
  """არსებული გარიგების მონაცემების განახლება Trade ID-ის (ან id-ის) მიხედვით."""
  try:
    supabase = get_data_client()
    response = (
        supabase.table("trades")
        .update(updated_data)
        .eq("Trade ID", trade_id)
        .execute()
    )
    if not response.data:
      supabase.table("trades").update(updated_data).eq("id", trade_id).execute()
    invalidate_trades()
    return True
  except Exception as e:
    st.error(f"ბაზის განახლების შეცდომა: {e}")
    return False


def delete_trade(trade_id):
  """გარიგების და მასთან დაკავშირებული ქვემოქმედებების წაშლა Trade ID-ის მიხედვით.
  წარმატებით წაშლის შემდეგ მათი სკრინშოტებიც იშლება Storage-იდან."""
  try:
    supabase = get_data_client()
    urls = []
    try:
      for col in ("Trade ID", "Parent Trade ID"):
        rows = supabase.table("trades").select("Screenshot").eq(col, trade_id).execute().data
        urls += [r.get("Screenshot") for r in (rows or [])]
    except Exception:
      urls = []
    supabase.table("trades").delete().eq("Trade ID", trade_id).execute()
    supabase.table("trades").delete().eq("Parent Trade ID", trade_id).execute()
    invalidate_trades()
    for url in set(u for u in urls if u):
      delete_screenshot(url)
    return True
  except Exception as e:
    st.error(f"ბაზიდან წაშლის შეცდომა: {e}")
    return False


# ---------------------------------------------------------------- settings
@st.cache_data(ttl=SETTINGS_TTL, show_spinner=False)
def _load_settings(uid, category):
  response = (
      get_data_client()
      .table("user_settings")
      .select("item_name")
      .eq("category", category)
      .execute()
  )
  return [row["item_name"] for row in response.data] if response.data else []


def fetch_settings(category):
  """კატეგორიის მიხედვით (მაგ: 'pattern' ან 'trigger') სიის წამოღება ბაზიდან."""
  try:
    return _load_settings(_uid(), category)
  except Exception:
    if category == "pattern":
      return ["ვ-შემობრუნება", "ორმაგი წვერი", "თავი მხრები"]
    return ["პინბარი", "ჩამყლაპავი", "გაფართოვება"]


def add_setting_item(category, item_name):
  try:
    get_data_client().table("user_settings").insert(
        {"category": category, "item_name": item_name}
    ).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


def delete_setting_item(category, item_name):
  try:
    get_data_client().table("user_settings").delete().eq(
        "category", category
    ).eq("item_name", item_name).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


def update_setting_item(category, old_name, new_name):
  try:
    get_data_client().table("user_settings").update(
        {"item_name": new_name}
    ).eq("category", category).eq("item_name", old_name).execute()
    _load_settings.clear()
    return True
  except Exception:
    return False


# ------------------------------------------------------- balance transactions
@st.cache_data(ttl=BALANCE_TTL, show_spinner=False)
def _load_balance(uid):
  response = get_data_client().table("balance_transactions").select("*").execute()
  return (
      pd.DataFrame(response.data)
      if response.data
      else pd.DataFrame(columns=BALANCE_COLUMNS)
  )


def fetch_balance_transactions():
  """ბრუნავს ტრანზაქციების DataFrame-ს."""
  try:
    return _load_balance(_uid())
  except Exception:
    return pd.DataFrame(columns=BALANCE_COLUMNS)


def add_balance_transaction(data):
  """ახალი ტრანზაქციის (შევსება/გამოტანა) დამატება ბაზაში."""
  try:
    get_data_client().table("balance_transactions").insert(data).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    st.error(f"შეცდომა ბაზაში ჩაწერისას: {e}")
    return False


def delete_balance_transaction(txn_id):
  """ტრანზაქციის წაშლა ID-ის მიხედვით."""
  try:
    get_data_client().table("balance_transactions").delete().eq(
        "Transaction ID", txn_id
    ).execute()
    _load_balance.clear()
    return True
  except Exception as e:
    st.error(f"შეცდომა ტრანზაქციის წაშლისას: {e}")
    return False


# ------------------------------------------------------------- screenshots
SCREENSHOT_BUCKET = "screenshots"
FULL_MAX_SIDE = 1600  # სრული სურათის მაქს. გვერდი (px)
FULL_QUALITY = 80
THUMB_MAX_SIDE = 360  # სიის პატარა პრევიუ
THUMB_QUALITY = 70
_PUBLIC_MARKER = f"/object/public/{SCREENSHOT_BUCKET}/"


def _prepare_images(raw):
  """აბრუნებს (სრული WebP, პატარა პრევიუ WebP) ბაიტებს, ან None თუ სურათი ვერ დამუშავდა.
  სრული სურათი მაქს. 1600px-ია, პრევიუ 360px (ჩვეულებრივ 10-30KB)."""
  try:
    from PIL import Image, ImageOps

    img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
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
  return text[idx + len(_PUBLIC_MARKER):].split("?")[0] or None


def _is_managed_path(path):
  """ახალი ფორმატი: <user_id>/<სახელი>.webp: მას პატარა პრევიუც აქვს და აპს შეუძლია წაშლა.
  ძველი ფაილები bucket-ის ძირშია და უცვლელი რჩება."""
  return bool(path) and "/" in path and path.endswith(".webp")


def thumb_url(url):
  """სიისთვის პატარა პრევიუს ბმული; ძველი სურათებისთვის იგივე ბმული."""
  path = _storage_path(url)
  if _is_managed_path(path):
    return str(url).split("?")[0][: -len(".webp")] + "_t.webp"
  return url


def delete_screenshot(url):
  """სურათს (და მის პრევიუს) შლის Storage-იდან. ძველ (ძირში მყოფ) ფაილებს არ ეხება."""
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


def upload_screenshot(uploaded_file, file_name=None):
  """სურათს ოპტიმიზაციის შემდეგ ტვირთავს <user_id>/ საქაღალდეში (+ პატარა პრევიუ)
  და აბრუნებს საჯარო ბმულს. file_name უკვე აღარ გამოიყენება: სახელი შემთხვევითია."""
  try:
    supabase = get_data_client()
    raw = uploaded_file.getvalue()
    folder = _uid() or "anon"
    token = uuid.uuid4().hex
    bucket = supabase.storage.from_(SCREENSHOT_BUCKET)
    options = {"upsert": "true", "cache-control": "31536000"}  # სახელი უნიკალურია: 1 წელი ქეში

    prepared = _prepare_images(raw)
    if prepared:
      full_bytes, thumb_bytes = prepared
      path = f"{folder}/{token}.webp"
      bucket.upload(path, full_bytes, {**options, "content-type": "image/webp"})
      try:
        bucket.upload(
            f"{folder}/{token}_t.webp", thumb_bytes, {**options, "content-type": "image/webp"}
        )
      except Exception:
        bucket.remove([path])  # ნახევრად ატვირთული ფაილი არ დავტოვოთ
        raise
      return bucket.get_public_url(path)

    # სურათი ვერ დამუშავდა (უცნაური ფორმატი): ორიგინალს ვტვირთავთ უცვლელად
    ext = os.path.splitext(file_name or "")[1].lower() or ".png"
    path = f"{folder}/{token}{ext}"
    bucket.upload(path, raw, {**options, "content-type": uploaded_file.type or "image/png"})
    return bucket.get_public_url(path)
  except Exception as e:
    st.error(f"სურათის ატვირთვის შეცდომა: {e}")
    return None


# ---------------------------------------------------------- user preferences
def fetch_user_preferences(user_id):
  """მოაქვს მომხმარებლის ვიზუალური პარამეტრები ბაზიდან (სესიაზე ერთხელ იძახება app.py-დან)."""
  try:
    response = (
        get_data_client()
        .table("user_preferences")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    if response.data and len(response.data) > 0:
      return response.data[0]
    return None
  except Exception as e:
    print(f"პარამეტრების წაკითხვის შეცდომა: {e}")
    return None


def upsert_user_preferences(user_id, mobile_mode=None, desktop_mode=None):
  """ანახლებს ან ამატებს მომხმარებლის პარამეტრებს ბაზაში."""
  try:
    data = {"user_id": user_id}
    if mobile_mode is not None:
      data["mobile_view_mode"] = mobile_mode
    if desktop_mode is not None:
      data["desktop_view_mode"] = desktop_mode

    get_data_client().table("user_preferences").upsert(
        data, on_conflict="user_id"
    ).execute()
    return True
  except Exception as e:
    st.error(f"ბაზის დეტალური შეცდომა: {e}")
    return False
