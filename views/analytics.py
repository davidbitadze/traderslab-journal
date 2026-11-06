from database import fetch_trades
from utils.formulas import calculate_stats
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
def _is_true(value):
  if isinstance(value, str):
    return value.strip().lower() == "true"
  return bool(value)


def _clean_label(value):
  if value is None or pd.isna(value) or not str(value).strip():
    return "N/A"
  return str(value).replace("|", "").strip() or "N/A"


def _collect_trades(df):
  """ამზადებს დასრულებული გარიგებების ცხრილს (თითო რიგი = ერთი გარიგება).
  P&L-ის ჯამები ერთი groupby-თი ითვლება (ნაცვლად ყოველი გარიგებისთვის მთელი ცხრილის გაფილტვრისა)."""
  main_trades = df[
      df["ActionType"].astype(str).str.contains("Start Row", case=False, na=False)
  ]
  if main_trades.empty:
    main_trades = df.drop_duplicates(subset=["Parent Trade ID"])

  if "Net P/L" in df.columns:
    pnl_values = pd.to_numeric(df["Net P/L"], errors="coerce").fillna(0.0)
  else:
    pnl_values = pd.Series(0.0, index=df.index)

  # გარიგების ჯამი = ყველა რიგი, სადაც Parent Trade ID == id, პლუს რიგი, სადაც Trade ID == id
  # (თუ ის Parent-ით სხვაა; ორმაგად არ ითვლება)
  by_parent = pnl_values.groupby(df["Parent Trade ID"]).sum()
  own_only = pnl_values.where(df["Parent Trade ID"] != df["Trade ID"], 0.0)
  by_own = own_only.groupby(df["Trade ID"]).sum()

  rows = []
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

    if not _is_true(trade.get("Finalized", False)):
      continue

    total_pnl = float(by_parent.get(trade_id, 0.0)) + float(by_own.get(trade_id, 0.0))

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
  return calculate_stats(d["PnL"])


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


def _group_table(g, key, label):
  """იღებს უკვე გამოთვლილ _group შედეგს (ორჯერ აღარ ითვლება)."""
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

  all_trades = _collect_trades(df)  # ერთხელ ითვლება და პერიოდების შედარებაშიც გამოიყენება
  if all_trades.empty:
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
    trades = all_trades.tail(int(period.split()[1])).reset_index(drop=True)
  else:
    trades = all_trades

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
  comp = []
  for label, count in [("ბოლო 100", 100), ("ბოლო 50", 50), ("ბოლო 20", 20), ("ბოლო 10", 10)]:
    ps = _stats(all_trades.tail(count))
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
      _group_table(g, "Day", "დღე")

  with tab_pair:
    g = _group(trades, "Pair")
    _bar(g, "Pair")
    _group_table(g, "Pair", "წყვილი")

  with tab_pattern:
    g = _group(trades, "Pattern")
    _bar(g, "Pattern")
    _group_table(g, "Pattern", "პატერნი")

  with tab_trigger:
    g = _group(trades, "Trigger")
    _bar(g, "Trigger")
    _group_table(g, "Trigger", "ტრიგერი")

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
    _group_table(g, "Side", "მიმართულება")
