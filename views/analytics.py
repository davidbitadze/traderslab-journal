from database import fetch_trades
from utils.dates import parse_trade_datetime
from utils.formulas import calculate_stats
from utils.trades import compute_pnl_map, split_trades
from utils.translations import t
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

DAYS_EN = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
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
  main_trades, subs_map = split_trades(df)
  if main_trades.empty:
    return pd.DataFrame()
  pnl_map = compute_pnl_map(main_trades, subs_map)

  rows = []
  for _, trade in main_trades.iterrows():
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")

    if not _is_true(trade.get("Finalized", False)):
      continue

    pattern = trade.get("Pattern")
    if pattern is None or pd.isna(pattern) or not str(pattern).strip():
      pattern = trade.get("Formation")

    rows.append({
        "Trade ID": trade_id,
        "Date": parse_trade_datetime(trade.get("Entry Date")),
        "Pair": _clean_label(trade.get("Pair")),
        "Side": _clean_label(trade.get("Side")),
        "Pattern": _clean_label(pattern),
        "Trigger": _clean_label(trade.get("Trigger")),
        "PnL": float(pnl_map.get(trade_id, 0.0)),
    })

  out = pd.DataFrame(rows)
  if out.empty:
    return out
  out["Date"] = pd.to_datetime(out["Date"])
  out = out.sort_values("Date", na_position="first").reset_index(drop=True)
  return out


def _stats(d):
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


def _group_table(g, key, label, lang):
  table = g.rename(
      columns={
          key: label,
          "Trades": t("table_trade_count", lang),
          "WinRate": t("table_win_rate", lang),
          "Total": t("table_total_pnl", lang),
          "Avg": t("table_avg_pnl", lang),
      }
  )[[label, t("table_trade_count", lang), t("table_win_rate", lang), t("table_total_pnl", lang), t("table_avg_pnl", lang)]]
  table[t("table_win_rate", lang)] = table[t("table_win_rate", lang)].round(0)
  _show_table(table, [t("table_total_pnl", lang), t("table_avg_pnl", lang)])


def _bar(g, key, value_col="Total", height=320):
  chart = g[[key, value_col]].copy()
  chart["Color"] = chart[value_col].apply(lambda v: GREEN if v >= 0 else RED)
  st.bar_chart(
      chart, x=key, y=value_col, color="Color", height=height, sort=False
  )


# ------------------------------------------------------------------- view
def render_analytics_view(lang="ka"):
  st.title(t("analytics_page_title", lang))

  df = fetch_trades()
  if df.empty:
    st.info(t("no_analytics_data", lang))
    return

  all_trades = _collect_trades(df)
  if all_trades.empty:
    st.info(t("no_finalized_trades", lang))
    return

  # ---- პერიოდის ფილტრი
  period_labels = [
      t("p_all", lang),
      t("p_100", lang),
      t("p_50", lang),
      t("p_20", lang),
      t("p_10", lang),
  ]
  period_raw = ["ყველა", "ბოლო 100", "ბოლო 50", "ბოლო 20", "ბოლო 10"]

  selected_period = st.radio(
      "period",
      period_labels,
      horizontal=True,
      label_visibility="collapsed",
  )

  # ვპოულობთ ინდექსს ორიგინალური ლოგიკისთვის
  idx = period_labels.index(selected_period)
  period = period_raw[idx]

  if period != "ყველა":
    trades = all_trades.tail(int(period.split()[1])).reset_index(drop=True)
  else:
    trades = all_trades

  s = _stats(trades)

  # ---- მთავარი ბარათები
  row1 = st.columns(4)
  with row1[0]:
    with st.container(border=True):
      st.metric(t("metric_total_pnl", lang), f"{s['total']:+.2f}$")
  with row1[1]:
    with st.container(border=True):
      st.metric(t("metric_win_rate", lang), f"{s['win_rate']:.1f}%", f"{s['wins']} / {s['losses']}", delta_color="off")
  with row1[2]:
    with st.container(border=True):
      st.metric(t("metric_pf", lang), _fmt(s["pf"]))
  with row1[3]:
    with st.container(border=True):
      st.metric(t("metric_expectancy", lang), _fmt(s["expectancy"], "{:+.2f}", "$"))

  row2 = st.columns(4)
  with row2[0]:
    with st.container(border=True):
      st.metric(t("metric_avg_win", lang), f"{s['avg_win']:.2f}$")
  with row2[1]:
    with st.container(border=True):
      st.metric(t("metric_avg_loss", lang), f"-{s['avg_loss']:.2f}$")
  with row2[2]:
    with st.container(border=True):
      st.metric(t("metric_payoff", lang), _fmt(s["payoff"]))
  with row2[3]:
    with st.container(border=True):
      st.metric(t("metric_trades_count", lang), s["n"])

  # ---- კაპიტალის მრუდი
  st.subheader(t("equity_curve_title", lang))
  equity = pd.DataFrame({
      t("equity_chart_x", lang): range(1, len(trades) + 1),
      t("equity_chart_y", lang): trades["PnL"].cumsum().round(2),
  })
  line_color = GREEN if s["total"] >= 0 else RED
  st.area_chart(
      equity, x=t("equity_chart_x", lang), y=t("equity_chart_y", lang), color=line_color, height=300
  )

  # ---- პერიოდების შედარება
  st.subheader(t("periods_comp_title", lang))
  comp = []
  for label, count in [(t("p_100", lang), 100), (t("p_50", lang), 50), (t("p_20", lang), 20), (t("p_10", lang), 10)]:
    ps = _stats(all_trades.tail(count))
    if ps:
      comp.append({
          t("table_period", lang): label,
          t("table_trade_count", lang): ps["n"],
          t("table_win_rate", lang): round(ps["win_rate"]),
          t("table_pf", lang): round(ps["pf"], 2) if ps["pf"] is not None else None,
          t("table_expectancy", lang): round(ps["expectancy"], 2),
          t("table_total_pnl", lang): round(ps["total"], 2),
      })
  if comp:
    _show_table(pd.DataFrame(comp), [t("table_expectancy", lang), t("table_total_pnl", lang)])

  st.divider()

  # ---- დეტალური ანალიზი ტაბებში
  tab_day, tab_pair, tab_pattern, tab_trigger, tab_side = st.tabs(
      [t("tab_day_label", lang), t("tab_pair_label", lang), t("tab_pattern_label", lang), t("tab_trigger_label", lang), t("tab_side_label", lang)]
  )

  days_list = DAYS_KA if lang == "ka" else DAYS_EN

  with tab_day:
    dated = trades.dropna(subset=["Date"]).copy()
    if dated.empty:
      st.info(t("insufficient_date_data", lang))
    else:
      days_map = dict(zip(range(7), days_list))
      dated["Day"] = dated["Date"].dt.weekday.map(lambda i: days_map[i])
      g = _group(dated, "Day")
      g["order"] = g["Day"].map({d: i for i, d in enumerate(days_list)})
      g = g.sort_values("order")
      _bar(g, "Day")
      _group_table(g, "Day", t("col_day", lang), lang)

  with tab_pair:
    g = _group(trades, "Pair")
    _bar(g, "Pair")
    _group_table(g, "Pair", t("col_pair", lang), lang)

  with tab_pattern:
    g = _group(trades, "Pattern")
    _bar(g, "Pattern")
    _group_table(g, "Pattern", t("col_pattern", lang), lang)

  with tab_trigger:
    g = _group(trades, "Trigger")
    _bar(g, "Trigger")
    _group_table(g, "Trigger", t("col_trigger", lang), lang)

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
    _group_table(g, "Side", t("col_side", lang), lang)
