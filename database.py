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


def get_supabase_client():
  """ავტორიზაციისთვის (app.py): ყოველ გამოძახებაზე ახალი კლიენტი, როგორც აქამდე.
  სესიის (login) მდგომარეობა სწორედ ამ კლიენტებზე ინახება, ამიტომ მათ არ ვინახავთ
  საერთო ქეშში — წინააღმდეგ შემთხვევაში ერთი მომხმარებლის ავტორიზაცია სხვებსაც გადაეცემოდა."""
  supabase_url = st.secrets["SUPABASE_URL"]
  supabase_key = st.secrets["SUPABASE_KEY"]
  return create_client(supabase_url, supabase_key)


@st.cache_resource
def get_data_client():
  """მონაცემების წასაკითხად/ჩასაწერად: ერთხელ იქმნება და მეხსიერებაში რჩება.
  აქ არასდროს ხდება sign_in, ამიტომ საერთო გამოყენება უსაფრთხოა."""
  return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


# ------------------------------------------------------------------ trades
@st.cache_data(ttl=TRADES_TTL, show_spinner=False)
def _load_trades():
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
    return _load_trades()
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
  """გარიგების და მასთან დაკავშირებული ქვემოქმედებების წაშლა Trade ID-ის მიხედვით."""
  try:
    supabase = get_data_client()
    supabase.table("trades").delete().eq("Trade ID", trade_id).execute()
    supabase.table("trades").delete().eq("Parent Trade ID", trade_id).execute()
    invalidate_trades()
    return True
  except Exception as e:
    st.error(f"ბაზიდან წაშლის შეცდომა: {e}")
    return False


# ---------------------------------------------------------------- settings
@st.cache_data(ttl=SETTINGS_TTL, show_spinner=False)
def _load_settings(category):
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
    return _load_settings(category)
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
def _load_balance():
  response = get_data_client().table("balance_transactions").select("*").execute()
  return (
      pd.DataFrame(response.data)
      if response.data
      else pd.DataFrame(columns=BALANCE_COLUMNS)
  )


def fetch_balance_transactions():
  """ბრუნავს ტრანზაქციების DataFrame-ს."""
  try:
    return _load_balance()
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
def _optimize_image(raw, max_side=1920, quality=85):
  """სურათს ამცირებს (მაქს. 1920px) და WebP-ში გადაჰყავს: ჩვეულებრივ 3-10-ჯერ მსუბუქია.
  შეცდომის ან უკეთესი შედეგის არარსებობისას აბრუნებს ორიგინალს."""
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
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=quality, method=4)
    data = out.getvalue()
    if len(data) < len(raw):
      return data, "image/webp", ".webp"
  except Exception:
    pass
  return raw, None, None


def upload_screenshot(uploaded_file, file_name=None):
  """სურათს ოპტიმიზაციის შემდეგ Supabase Storage-ში ტვირთავს და აბრუნებს საჯარო ბმულს."""
  try:
    supabase = get_data_client()

    # სახელის უსაფრთხო დამუშავება (სფეისების და კონფლიქტური სიმბოლოების მოცილება)
    if file_name:
      clean_name = re.sub(r"[^a-zA-Z0-9.\-_]", "_", file_name)
    else:
      clean_name = "trade_screenshot.png"

    data, content_type, new_ext = _optimize_image(uploaded_file.getvalue())
    if content_type:
      clean_name = os.path.splitext(clean_name)[0] + new_ext
    else:
      content_type = uploaded_file.type or "image/png"

    unique_file_name = f"{uuid.uuid4().hex[:6]}_{clean_name}"

    supabase.storage.from_("screenshots").upload(
        unique_file_name,
        data,
        {
            "content-type": content_type,
            "upsert": "true",
            # სახელი უნიკალურია, ამიტომ ბრაუზერს შეუძლია სურათი 1 წელი შეინახოს
            "cache-control": "31536000",
        },
    )
    return supabase.storage.from_("screenshots").get_public_url(unique_file_name)
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
