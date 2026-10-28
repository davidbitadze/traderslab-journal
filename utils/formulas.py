import math

DEFAULT_RISK_USD = 5.85

_LONG_ALIASES = {"long", "ზრდა (long)", "buy"}
_SHORT_ALIASES = {"short", "კლება (short)", "sell"}

def to_float(value, default=0.0):
  try:
    if value is None:
      return default
    result = float(value)
    return default if math.isnan(result) else result
  except (ValueError, TypeError):
    return default

def normalize_side(side):
  s = str(side or "").strip().lower()
  if s in _LONG_ALIASES:
    return "long"
  if s in _SHORT_ALIASES:
    return "short"
  return None

def calculate_net_pnl(main, subs):
  side = main.get("Side", "")
  risk = to_float(main.get("Risk ($)"), DEFAULT_RISK_USD)
  direction = normalize_side(side)

  if direction is None:
    return 0.0

  main_entry_price = to_float(main.get("Entry Price"))
  main_qty = to_float(main.get("Qty"))

  entry_legs = [(main_entry_price, main_qty)]
  
  for _, s in subs.iterrows():
    act_type = str(s.get("ActionType", ""))
    if any(term in act_type.lower() for term in ["scale in", "დამატებითი შესვლა"]):
      entry_legs.append(
          (to_float(s.get("Entry Price")), to_float(s.get("Qty")))
      )

  total_entry_qty = sum(q for _, q in entry_legs)
  if total_entry_qty > 0:
    avg_entry_price = sum(p * q for p, q in entry_legs) / total_entry_qty
  else:
    avg_entry_price = main_entry_price

  if avg_entry_price == 0:
    return 0.0

  exits = []
  for _, s in subs.iterrows():
    act_type = str(s.get("ActionType", "")).lower()
    # ვფარავთ როგორც ქართულ, ისე ინგლისურ ვარიანტებს
    if any(term in act_type for term in ["exit", "დახურვა", "close", "ნაწილობრივი", "სრული", "partial", "full"]):
      exits.append((
          to_float(s.get("Entry Price"), avg_entry_price),
          to_float(s.get("Qty"))
      ))

  if not exits:
    # თუ ქვედა ეტაპებიდან ვერ წამოიღო, ვცდილობთ მთავარი გარიგების ველებიდან
    return None

  total_pnl = 0.0
  for ex_price, ex_qty in exits:
    if ex_qty <= 0:
      continue
    
    if direction == "long":
      price_diff = ex_price - avg_entry_price
    else:
      price_diff = avg_entry_price - ex_price

    move_percentage = (price_diff / avg_entry_price) * 100
    qty_share = ex_qty / total_entry_qty if total_entry_qty > 0 else 1.0
    
    stage_pnl = risk * move_percentage * qty_share
    total_pnl += stage_pnl

  return round(total_pnl, 2)
