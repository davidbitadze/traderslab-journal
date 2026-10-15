from database import fetch_trades
import pandas as pd
import streamlit as st

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"

DAYS_KA = [
    "ორშაბათი",
    "სამშაბათი",
    "ოთხშაბათი",
    "ხუთშაბათი",
    "პარასკევი",
    "შაბათი",
    "კვირა",
]


# ---------------------------------------------------------------- helpers
def _num(value, default=0.0):
  try:
    if value is None or pd.isna(value) or str(value).strip() in ("", "None"):
      return default
    return float(value)
  except (ValueError, TypeError):
    return default


def _is_true(value):
  if isinstance(value, str):
    return value.strip().lower() == "true"
  return bool(value)


def _clean_label(value):
  if value is None or pd.isna(value) or not str(value).strip():
    return "N/A"
  return str(value).replace("|", "").strip() or "N/A"


def _collect_trades(df):
  """ამზადებს დასრულებული გარიგებების ცხრილს (თითო რიგი = ერთი გარიგება)."""
  main_trades = df[
      df["ActionType"].astype(str).str.contains("Start Row", case=False, na=False)
  ]
  if main_trades.empty:
    main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

  rows = []
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

    if not _is_true(trade.get("Finalized", False)):
      continue

    related = df[
        (df["Parent Trade ID"] == trade_id) | (df["Trade ID"] == trade_id)
    ]
    total_pnl = sum(_num(v) for v in related["Net P/L"]) if "Net P/L" in related else 0.0

    pattern = trade.get("Pattern")
    if pattern is None or pd.isna(pattern) or not str(pattern).strip():
      pattern = trade.get("Formation")

    rows.append({
        "Trade ID": trade_id,
        "Date": pd.to_datetime(trade.get("Entry Date"), errors="coerce"),
        "Pair": _clean_label(trade.get("Pair")),
        "Side": _clean_label(trade.get("Side")),
        "Pattern": _clean_label(pattern),
        "Trigger": _clean_label(trade.get("Trigger")),
        "PnL": total_pnl,
    })

  out = pd.DataFrame(rows)
  if out.empty:
    return out
  out = out.sort_values("Date", na_position="first").reset_index(drop=True)
  return out


def _stats(d):
  """ძირითადი მაჩვენებლები გარიგებების ნებისმიერი ჩანაკვეთისთვის."""
  n = len(d)
  if n == 0:
    return None
  wins = d[d["PnL"] > 0]["PnL"]
  losses = d[d["PnL"] < 0]["PnL"]
  gross_win = wins.sum()
  gross_loss = abs(losses.sum())
  avg_win = wins.mean() if len(wins) else 0.0
  avg_loss = abs(losses.mean()) if len(losses) else 0.0
  win_rate = len(wins) / n * 100
  return {
      "n": n,
      "total": d["PnL"].sum(),
      "win_rate": win_rate,
      "wins": len(wins),
      "losses": len(losses),
      "avg_win": avg_win,
      "avg_loss": avg_loss,
      "payoff": (avg_win / avg_loss) if avg_loss > 0 else None,
      "pf": (gross_win / gross_loss) if gross_loss > 0 else None,
      "expectancy": d["PnL"].mean(),
  }


def _fmt(value, spec="{:.2f}", suffix=""):
  return "—" if value is None else spec.format(value) + suffix


def _color_pnl(value):
  if isinstance(value, (int, float)):
    if value > 0:
      return f"color: {GREEN}; font-weight: 600"
    if value < 0:
      return f"color: {RED}; font-weight: 600"
  return ""


def _show_table(table, pnl_cols):
  styler = table.style.format({c: "{:+.2f}" for c in pnl_cols})
  apply = styler.map if hasattr(styler, "map") else styler.applymap
  styler = apply(_color_pnl, subset=pnl_cols)
  st.dataframe(styler, use_container_width=True, hide_index=True)


def _group(d, key):
  g = (
      d.groupby(key)
      .agg(
          Trades=("PnL", "count"),
          Wins=("PnL", lambda s: (s > 0).sum()),
          Total=("PnL", "sum"),
          Avg=("PnL", "mean"),
      )
      .reset_index()
  )
  g["WinRate"] = g["Wins"] / g["Trades"] * 100
  return g.sort_values("Total", ascending=False).reset_index(drop=True)


def _group_table(d, key, label):
  g = _group(d, key)
  table = g.rename(
      columns={
          key: label,
          "Trades": "გარიგება",
          "WinRate": "Win Rate %",
          "Total": "ჯამური P&L",
          "Avg": "საშუალო P&L",
      }
  )[[label, "გარიგება", "Win Rate %", "ჯამური P&L", "საშუალო P&L"]]
  table["Win Rate %"] = table["Win Rate %"].round(0)
  _show_table(table, ["ჯამური P&L", "საშუალო P&L"])
  return g


def _bar(g, key, value_col="Total", height=320):
  chart = g[[key, value_col]].copy()
  chart["Color"] = chart[value_col].apply(lambda v: GREEN if v >= 0 else RED)
  st.bar_chart(
      chart, x=key, y=value_col, color="Color", height=height, sort=False
  )


# ------------------------------------------------------------------- view
def render_analytics_view(lang="ka"):
  st.title("📈 სტატისტიკა და ანალიტიკა")

  df = fetch_trades()
  if df.empty:
    st.info("ანალიტიკისთვის მონაცემები ჯერ არ არის ჟურნალში.")
    return

  trades = _collect_trades(df)
  if trades.empty:
    st.info(
        "დასრულებული (Finalized) გარიგებები ანალიტიკისთვის ჯერ არ მოიძებნა."
    )
    return

  # ---- პერიოდის ფილტრი
  period = st.radio(
      "პერიოდი",
      ["ყველა", "ბოლო 100", "ბოლო 50", "ბოლო 20", "ბოლო 10"],
      horizontal=True,
      label_visibility="collapsed",
  )
  if period != "ყველა":
    trades = trades.tail(int(period.split()[1])).reset_index(drop=True)

  s = _stats(trades)

  # ---- მთავარი ბარათები
  row1 = st.columns(4)
  with row1[0]:
    with st.container(border=True):
      st.metric("ჯამური P&L", f"{s['total']:+.2f}$")
  with row1[1]:
    with st.container(border=True):
      st.metric("Win Rate", f"{s['win_rate']:.1f}%", f"{s['wins']} / {s['losses']}", delta_color="off")
  with row1[2]:
    with st.container(border=True):
      st.metric("Profit Factor", _fmt(s["pf"]))
  with row1[3]:
    with st.container(border=True):
      st.metric("მოლოდინი (Expectancy)", _fmt(s["expectancy"], "{:+.2f}", "$"))

  row2 = st.columns(4)
  with row2[0]:
    with st.container(border=True):
      st.metric("საშ. მოგება", f"{s['avg_win']:.2f}$")
  with row2[1]:
    with st.container(border=True):
      st.metric("საშ. ზარალი", f"-{s['avg_loss']:.2f}$")
  with row2[2]:
    with st.container(border=True):
      st.metric("Payoff Ratio", _fmt(s["payoff"]))
  with row2[3]:
    with st.container(border=True):
      st.metric("გარიგებები", s["n"])

  # ---- კაპიტალის მრუდი
  st.subheader("💹 კაპიტალის მრუდი")
  equity = pd.DataFrame({
      "გარიგება #": range(1, len(trades) + 1),
      "კუმულაციური P&L": trades["PnL"].cumsum().round(2),
  })
  line_color = GREEN if s["total"] >= 0 else RED
  st.area_chart(
      equity, x="გარიგება #", y="კუმულაციური P&L", color=line_color, height=300
  )

  # ---- პერიოდების შედარება
  st.subheader("🔄 პერიოდების შედარება")
  full = _collect_trades(df)
  comp = []
  for label, count in [("ბოლო 100", 100), ("ბოლო 50", 50), ("ბოლო 20", 20), ("ბოლო 10", 10)]:
    ps = _stats(full.tail(count))
    if ps:
      comp.append({
          "პერიოდი": label,
          "გარიგება": ps["n"],
          "Win Rate %": round(ps["win_rate"]),
          "Profit Factor": round(ps["pf"], 2) if ps["pf"] is not None else None,
          "მოლოდინი": round(ps["expectancy"], 2),
          "ჯამური P&L": round(ps["total"], 2),
      })
  if comp:
    _show_table(pd.DataFrame(comp), ["მოლოდინი", "ჯამური P&L"])

  st.divider()

  # ---- დეტალური ანალიზი ტაბებში
  tab_day, tab_pair, tab_pattern, tab_trigger, tab_side = st.tabs(
      ["📅 კვირის დღე", "💱 წყვილი", "📌 პატერნი", "⚡ ტრიგერი", "↕️ Long / Short"]
  )

  with tab_day:
    dated = trades.dropna(subset=["Date"]).copy()
    if dated.empty:
      st.info("თარიღების მონაცემი არასაკმარისია.")
    else:
      dated["Day"] = dated["Date"].dt.weekday.map(lambda i: DAYS_KA[i])
      g = _group(dated, "Day")
      g["order"] = g["Day"].map({d: i for i, d in enumerate(DAYS_KA)})
      g = g.sort_values("order")
      _bar(g, "Day")
      _group_table(dated, "Day", "დღე")

  with tab_pair:
    g = _group(trades, "Pair")
    _bar(g, "Pair")
    _group_table(trades, "Pair", "წყვილი")

  with tab_pattern:
    g = _group(trades, "Pattern")
    _bar(g, "Pattern")
    _group_table(trades, "Pattern", "პატერნი")

  with tab_trigger:
    g = _group(trades, "Trigger")
    _bar(g, "Trigger")
    _group_table(trades, "Trigger", "ტრიგერი")

  with tab_side:
    g = _group(trades, "Side")
    total = g["Trades"].sum()
    cols = st.columns(max(len(g), 1))
    for col, (_, row) in zip(cols, g.iterrows()):
      with col:
        with st.container(border=True):
          st.metric(
              f"{row['Side']} ({row['Trades'] / total * 100:.0f}%)",
              f"{row['Total']:+.2f}$",
              f"Win Rate {row['WinRate']:.0f}%",
              delta_color="off",
          )
    _group_table(trades, "Side", "მიმართულება")
