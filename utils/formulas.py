import math

DEFAULT_RISK_USD = 5.85

_LONG_ALIASES = {"long", "ზრდა (long)", "buy"}
_SHORT_ALIASES = {"short", "კლება (short)", "sell"}


def to_float(value, default=0.0):
  """უსაფრთხო float: ცარიელი, None, NaN და ტექსტი -> default."""
  try:
    if value is None:
      return default
    result = float(value)
    return default if math.isnan(result) else result
  except (ValueError, TypeError):
    return default


def normalize_side(side):
  """აბრუნებს 'long', 'short' ან None."""
  s = str(side or "").strip().lower()
  if s in _LONG_ALIASES:
    return "long"
  if s in _SHORT_ALIASES:
    return "short"
  return None


def calculate_trade_pnl(
    entry_price, exit_price, risk_usd, side="Long", round_result=True
):
  """ერთი გასვლის P&L გაანგარიშება."""
  entry = to_float(entry_price)
  risk = to_float(risk_usd)
  direction = normalize_side(side)

  if entry == 0 or risk == 0 or direction is None:
    return 0.0

  exit_ = to_float(exit_price)
  if exit_ == 0:
    exit_ = entry

  diff = (exit_ - entry) if direction == "long" else (entry - exit_)
  result = risk * (diff / entry) * 100
  return round(result, 2) if round_result else result


def calculate_net_pnl(main, subs):
  """გარიგების Net P/L: თითოეული ეტაპის წილობრივი დამოუკიდებელი კალკულაცია."""
  side = main.get("Side", "")
  risk = to_float(main.get("Risk ($)"), DEFAULT_RISK_USD)
  direction = normalize_side(side)

  if direction is None:
    return 0.0

  # 1. მთავარი შესვლა
  main_entry_price = to_float(main.get("Entry Price"))
  main_qty = to_float(main.get("Qty"))

  entry_legs = [(main_entry_price, main_qty)]
  
  # 2. დამატებითი შესვლები (Scale In / დამატებითი შესვლა)
  for _, s in subs.iterrows():
    act_type = str(s.get("ActionType", ""))
    if any(term in act_type for term in ["Scale In", "დამატებითი შესვლა"]):
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

  # 3. გასვლები (Exit / დახურვა / ნაწილობრივი / სრული)
  exits = []
  for _, s in subs.iterrows():
    act_type = str(s.get("ActionType", ""))
    if any(term in act_type for term in ["Exit", "დახურვა", "Close", "ნაწილობრივი", "სრული"]):
      exits.append((
          to_float(s.get("Entry Price"), avg_entry_price),
          to_float(s.get("Qty"))
      ))

  if not exits:
    return None

  total_pnl = 0.0

  # თითოეული გამოსვლისთვის ვთვლით მის რეალურ წილს და მოგება/ზარალს
  for ex_price, ex_qty in exits:
    if ex_qty <= 0:
      continue
    
    if direction == "long":
      price_diff = ex_price - avg_entry_price
    else:
      price_diff = avg_entry_price - ex_price

    # ამ კონკრეტული ეტაპის პროცენტული ცვლილება
    move_percentage = (price_diff / avg_entry_price) * 100

    # ამ ეტაპის წილი მთლიან მოცულობასთან (ანუ რამდენი პროცენტი დაიხურა ამ ნაბიჯით)
    qty_share = ex_qty / total_entry_qty if total_entry_qty > 0 else 1.0

    # ამ ეტაპის დოლარული მოგება/ზარალი
    stage_pnl = risk * move_percentage * qty_share
    total_pnl += stage_pnl

  return round(total_pnl, 2)


def calculate_stats(pnls):
  """ძირითადი მაჩვენებლები P&L-ების სიისთვის."""
  values = [to_float(p) for p in pnls]
  n = len(values)
  if n == 0:
    return None

  wins = [v for v in values if v > 0]
  losses = [v for v in values if v < 0]
  gross_win = sum(wins)
  gross_loss = abs(sum(losses))
  avg_win = gross_win / len(wins) if wins else 0.0
  avg_loss = gross_loss / len(losses) if losses else 0.0

  return {
      "n": n,
      "total": sum(values),
      "win_rate": len(wins) / n * 100,
      "wins": len(wins),
      "losses": len(losses),
      "avg_win": avg_win,
      "avg_loss": avg_loss,
      "payoff": (avg_win / avg_loss) if avg_loss > 0 else None,
      "pf": (gross_win / gross_loss) if gross_loss > 0 else None,
      "expectancy": sum(values) / n,
  }
