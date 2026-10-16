import math

# თუ გარიგებას Risk ($) არ აქვს ჩაწერილი, ამ მნიშვნელობით ითვლება.
# გააზრებულად გადაწყვიტე, გინდა თუ არა ეს დეფოლტი: ის არასწორ რიცხვებს გამოიმუშავებს.
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
  """აბრუნებს 'long', 'short' ან None (თუ მიმართულება უცნობია)."""
  s = str(side or "").strip().lower()
  if s in _LONG_ALIASES:
    return "long"
  if s in _SHORT_ALIASES:
    return "short"
  return None


def calculate_trade_pnl(
    entry_price, exit_price, risk_usd, side="Long", round_result=True
):
  """ერთი გასვლის P&L: risk * (ფასის ცვლილება %).

  უცნობი მიმართულების, ნულოვანი შესვლის ფასის ან ნულოვანი რისკის შემთხვევაში 0.0.
  round_result=False ნიშნავს დამრგვალების გარეშე (ჯამებში დაგროვილი ცდომილების თავიდან ასაცილებლად).
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


def calculate_net_pnl(main, subs):
  """გარიგების Net P/L (რეალიზებული).

  main: მთავარი რიგი (Series ან dict), subs: ამ გარიგების ეტაპების DataFrame.
  შესვლა = საწყისი რიგი + Scale In-ები (საშუალო შეწონილი ფასი).
  ყოველი Exit თავისი წილით (Qty / შესვლის მოცულობა) ითვლება.
  აბრუნებს None-ს, თუ Exit საერთოდ არ არის.
  """
  side = main.get("Side", "")
  risk = to_float(main.get("Risk ($)"), DEFAULT_RISK_USD)

  entry_legs = [(to_float(main.get("Entry Price")), to_float(main.get("Qty")))]
  for _, s in subs.iterrows():
    if "Scale In" in str(s.get("ActionType", "")):
      entry_legs.append(
          (to_float(s.get("Entry Price")), to_float(s.get("Qty")))
      )

  entry_qty = sum(q for _, q in entry_legs)
  if entry_qty > 0:
    entry_p = sum(p * q for p, q in entry_legs) / entry_qty
  else:
    entry_p = entry_legs[0][0]

  exits = [
      (to_float(s.get("Entry Price"), entry_p), to_float(s.get("Qty")))
      for _, s in subs.iterrows()
      if "Exit" in str(s.get("ActionType", ""))
  ]
  if not exits:
    return None

  # თუ შესვლის მოცულობა არ არის ჩაწერილი, წილებს გასვლების ჯამიდან ვითვლით
  denom = entry_qty if entry_qty > 0 else sum(q for _, q in exits)

  total = 0.0
  for ex_p, ex_q in exits:
    share = (ex_q / denom) if denom > 0 else 1.0 / len(exits)
    total += (
        calculate_trade_pnl(entry_p, ex_p, risk, side, round_result=False)
        * share
    )
  return round(total, 2)


def calculate_stats(pnls):
  """ძირითადი მაჩვენებლები P&L-ების სიისთვის. ცარიელზე აბრუნებს None-ს."""
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
