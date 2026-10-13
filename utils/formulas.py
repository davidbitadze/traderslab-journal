
def calculate_trade_pnl(entry_price, exit_price, risk_usd, side="Long"):
  """
  გამოთვლის რეალურ მოგება/წაგებას (Real Profit) იუზერის მიერ მოთხოვნილი ლოგიკით:
  შესვლისა და გამოსვლის ფასებით ნთვალდება კოეფიციენტი და მრავლდება რისკში მითითებულ დოლარზე.
  """
  try:
    e_price = float(entry_price)
    ex_price = float(exit_price) if exit_price else e_price
    risk = float(risk_usd) if risk_usd else 0.0

    if e_price == 0:
      return 0.0

    # კოეფიციენტის გამოთვლა მიმართულების მიხედვით
    if side.lower() == "long" or side == "ზრდა (Long)":
      coefficient = (ex_price - e_price) / e_price
    else:
      coefficient = (e_price - ex_price) / e_price

    # Real Profit = Risk ($) x Effective R/R / Coefficient scaling
    result = risk * (coefficient * 100)  # პირობითი სკალირება პროცენტული კოეფიციენტიდან
    return round(result, 2)
  except Exception:
    return 0.0
