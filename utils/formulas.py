import math


def calculate_trade_pnl(entry_price, exit_price, risk_usd, side="Long"):
  """გამოთვლის რეალურ მოგება/წაგებას (Real Profit) და აზღვევს NaN შედეგებს."""
  try:
    e_price = float(entry_price) if entry_price else 0.0
    ex_price = float(exit_price) if exit_price else e_price
    
    # ვამოწმებთ რისკის მნიშვნელობას (თუ NaN-ია ან ცარიელია, ვანიჭებთ 0.0-ს)
    if risk_usd is None or (isinstance(risk_usd, float) and math.isnan(risk_usd)):
      risk = 0.0
    else:
      try:
        risk = float(risk_usd)
      except (ValueError, TypeError):
        risk = 0.0

    if e_price == 0 or risk == 0:
      return 0.0

    # მიმართულება
    is_long = side.lower() in ["long", "ზრდა (long)", "buy"]

    if is_long:
      diff = ex_price - e_price
    else:
      diff = e_price - ex_price

    ratio = diff / e_price
    result = risk * ratio * 100

    # საბოლოო შემოწმება, რომ შედეგი არ იყოს NaN
    if math.isnan(result):
      return 0.0

    return round(result, 2)
  except Exception:
    return 0.0
