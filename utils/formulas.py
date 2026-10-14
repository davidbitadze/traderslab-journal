def calculate_trade_pnl(entry_price, exit_price, risk_usd, side="Long"):
  try:
    e_price = float(entry_price)
    ex_price = float(exit_price) if exit_price else e_price
    risk = float(risk_usd) if risk_usd else 0.0

    if e_price == 0:
      return 0.0

    # მიმართულება
    is_long = side.lower() in ["long", "ზრდა (long)", "buy"]

    if is_long:
      diff = ex_price - e_price
    else:
      diff = e_price - ex_price

    # Real Profit = Risk ($) x Effective R/R
    # სადაც Effective R/R არის მიმდინარე ფასის სხვაობის შეფარდება საწყის ცვლილებასთან
    # თუ ზუსტ კოეფიციენტს ითვლით, შეგიძლიათ პირდაპირ მიამმაპოთ:
    ratio = diff / e_price
    result = risk * ratio * 100  # სკალირების კოეფიციენტი ლოტებისა და პიპების მიხედვით

    return round(result, 2)
  except Exception:
    return 0.0
