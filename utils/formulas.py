import math

DEFAULT_RISK_USD = 5.85

# SL-ის ვალიდაცია: თუ SL არასწორ მხარესაა, ან შესვლიდან ძალიან შორსაა, ან ფორმის
# ნაგულისხმევი 1.0000-ია, მას არ ვიყენებთ და ვრჩებით ძველ %-ზე დაფუძნებულ გამოთვლაზე.
MAX_STOP_PCT = 0.08
PLACEHOLDER_STOPS = (1.0,)

ENTRY_TERMS = ("Scale In", "დამატებითი შესვლა")
EXIT_TERMS = ("Exit", "დახურვა", "Close", "ნაწილობრივი", "სრული")

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
  """ძველი %-ზე დაფუძნებული გამოთვლა: risk * (ფასის ცვლილება %).

  რჩება როგორც სარეზერვო ვარიანტი (მაგ. როცა SL ფასი არ არის მითითებული).
  """
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


def _has_term(action, terms):
  text = str(action or "")
  return any(term in text for term in terms)


def pnl_breakdown(main, subs):
  """გარიგების Net P/L და მისი გამოთვლის ყველა ნაბიჯი.

  ძირითადი ფორმულა (R-მულტიპლიკატორი):
      R   = (შეწონილი გასვლის ფასი - შესვლის ფასი) / (შესვლის ფასი - SL)   [Long]
      R   = (შესვლის ფასი - შეწონილი გასვლის ფასი) / (SL - შესვლის ფასი)   [Short]
      P/L = R * Risk($) * დახურული წილი (გასვლის Qty / შესვლის Qty, მაქს. 1)
  Risk($) ხელით მითითებული თანხაა: რა იქნებოდა ზარალი SL-ზე (საკომისიოსა და
  სვოპის ჩათვლით, ბროკერის მონაცემით).

  თუ SL ვალიდური არ არის, ვიყენებთ ძველ ფორმულას: Risk * (საშ. ცვლილება %) * 100.

  აბრუნებს None-ს, თუ გასვლის ეტაპი საერთოდ არ არის.
  """
  direction = normalize_side(main.get("Side", ""))
  risk = to_float(main.get("Risk ($)"), DEFAULT_RISK_USD)

  entry_legs = [(to_float(main.get("Entry Price")), to_float(main.get("Qty")))]
  exit_rows = []
  for _, s in subs.iterrows():
    action = s.get("ActionType", "")
    if _has_term(action, ENTRY_TERMS):
      entry_legs.append((to_float(s.get("Entry Price")), to_float(s.get("Qty"))))
    elif _has_term(action, EXIT_TERMS):
      exit_rows.append(s)

  if not exit_rows:
    return None

  entry_qty = sum(q for _, q in entry_legs)
  if entry_qty > 0:
    avg_entry = sum(p * q for p, q in entry_legs) / entry_qty
  else:
    avg_entry = entry_legs[0][0]

  result = {
      "method": "invalid",
      "pnl": 0.0,
      "direction": direction,
      "risk": risk,
      "entry_avg": avg_entry,
      "entry_qty": entry_qty,
      "exit_avg": None,
      "exit_qty": 0.0,
      "closed_fraction": 1.0,
      "stop_price": None,
      "stop_dist": None,
      "profit_per_unit": None,
      "r_multiple": None,
  }
  if direction is None or avg_entry <= 0:
    return result

  # გასვლები: ფასი <= 0 ნიშნავს "არ არის შევსებული" -> უცვლელი (შესვლის ფასი)
  exits = []
  for s in exit_rows:
    price = to_float(s.get("Entry Price"))
    exits.append((price if price > 0 else avg_entry, to_float(s.get("Qty"))))

  exit_qty = sum(q for _, q in exits if q > 0)
  if exit_qty > 0:
    exit_avg = sum(p * q for p, q in exits if q > 0) / exit_qty
  else:  # Qty არ არის მითითებული: თანაბარი წონები
    exit_avg = sum(p for p, _ in exits) / len(exits)

  closed_fraction = 1.0
  if entry_qty > 0 and exit_qty > 0:
    closed_fraction = min(1.0, exit_qty / entry_qty)

  if direction == "long":
    profit = exit_avg - avg_entry
  else:
    profit = avg_entry - exit_avg

  stop = to_float(main.get("SL_Price"))
  stop_dist = (avg_entry - stop) if direction == "long" else (stop - avg_entry)
  placeholder = any(abs(stop - p) < 1e-9 for p in PLACEHOLDER_STOPS)
  stop_ok = (
      stop > 0 and not placeholder and 0 < stop_dist <= MAX_STOP_PCT * avg_entry
  )

  result.update(
      exit_avg=exit_avg,
      exit_qty=exit_qty,
      closed_fraction=closed_fraction,
      profit_per_unit=profit,
      stop_price=stop if stop > 0 else None,
  )

  if stop_ok:
    r_multiple = profit / stop_dist
    result.update(
        method="R",
        stop_dist=stop_dist,
        r_multiple=r_multiple,
        pnl=round(risk * r_multiple * closed_fraction, 2),
    )
  else:
    result.update(
        method="legacy",
        pnl=round(risk * (profit / avg_entry) * 100, 2),
    )
  return result


def calculate_net_pnl(main, subs):
  """გარიგების Net P/L (რიცხვი), ან None თუ გასვლის ეტაპი არ არის."""
  breakdown = pnl_breakdown(main, subs)
  return None if breakdown is None else breakdown["pnl"]


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
