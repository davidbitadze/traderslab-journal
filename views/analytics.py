import re
from database import fetch_trades
from utils.dates import parse_trade_datetime
from utils.formulas import calculate_stats
from utils.trades import compute_pnl_map, split_trades
from utils.translations import t
import altair as alt
import pandas as pd
import streamlit as st

GREEN = "#22c55e"
RED = "#ef4444"
GRAY = "#94a3b8"

_AI_CRITERIA_KEYS = ["level", "pattern", "trigger", "volume", "management"]
_AI_CRITERIA_LABELS_KA = [
    "📍 დონე",
    "🧩 პატერნი",
    "⚡ ტრიგერი",
    "📊 მოცულობა/ფონი",
    "🛡️ მართვა",
]
_AI_CRITERIA_LABELS_EN = [
    "📍 Level",
    "🧩 Pattern",
    "⚡ Trigger",
    "📊 Volume/Context",
    "🛡️ Management",
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


def _chart_palette():
  is_light = st.session_state.get("theme_mode") == "light"
  if is_light:
    return {
        "bg": "#FFFFFF",
        "text": "#0F172A",
        "grid": "#E2E8F0",
        "bar_pos": "#16A34A",
        "bar_neg": "#DC2626",
        "ai_bar": "#2563EB",
        "ai_line": "#059669",
        "eq_pos": "#16A34A",
        "eq_neg": "#DC2626",
    }
  return {
      "bg": "#0F172A",
      "text": "#E2E8F0",
      "grid": "#1E293B",
      "bar_pos": GREEN,
      "bar_neg": RED,
      "ai_bar": "#38BDF8",
      "ai_line": "#34D399",
      "eq_pos": GREEN,
      "eq_neg": RED,
  }


def _apply_altair_theme(chart, palette, height):
  return (
      chart.properties(height=height, background=palette["bg"])
      .configure_view(stroke=palette["grid"], fill=palette["bg"])
      .configure_axis(
          labelColor=palette["text"],
          titleColor=palette["text"],
          gridColor=palette["grid"],
          domainColor=palette["grid"],
          tickColor=palette["grid"],
      )
  )


def _parse_ai_scores(raw):
  """აბრუნებს [s1, s2, s3, s4, s5] float სიას (0..2) ან None-ს, თუ ვალიდური ქულები არ არის."""
  if raw is None:
    return None
  if isinstance(raw, float) and pd.isna(raw):
    return None

  if isinstance(raw, (list, tuple)):
    parts = list(raw)
  else:
    text = str(raw).strip()
    if not text or text.lower() in ("nan", "none", "<na>"):
      return None
    text = re.sub(r"^SCORES:\s*", "", text, flags=re.I)
    parts = [p.strip() for p in text.split(",")]

  if len(parts) != 5:
    return None

  vals = []
  for p in parts:
    try:
      v = float(p)
    except (ValueError, TypeError):
      return None
    if v < 0 or v > 2:
      return None
    vals.append(v)
  return vals


def _collect_ai_scores(df):
  """აგროვებს AI შეფასებებს მთავარი გარიგებებიდან ქრონოლოგიურად."""
  main_trades, _ = split_trades(df)
  if main_trades.empty or "ai_scores" not in main_trades.columns:
    return pd.DataFrame()

  rows = []
  for _, trade in main_trades.iterrows():
    parsed = _parse_ai_scores(trade.get("ai_scores"))
    if not parsed:
      continue
    trade_id = trade.get("Trade ID") or trade.get("Parent Trade ID")
    total_10 = round(sum(parsed), 2)
    row = {
        "Trade ID": trade_id,
        "Date": parse_trade_datetime(trade.get("Entry Date")),
        "Pair": _clean_label(trade.get("Pair")),
        "AI_Total": total_10,
    }
    for k, v in zip(_AI_CRITERIA_KEYS, parsed):
      row[k] = v
    rows.append(row)

  out = pd.DataFrame(rows)
  if out.empty:
    return out
  out["Date"] = pd.to_datetime(out["Date"])
  out = out.sort_values("Date", na_position="first").reset_index(drop=True)
  return out


def _render_ai_scores_section(df, lang="ka"):
  st.divider()
  st.subheader(
      "🤖 AI მენტორის ქულების სტატისტიკა"
      if lang == "ka"
      else "🤖 AI Mentor Score Statistics"
  )

  ai_df = _collect_ai_scores(df)
  if ai_df.empty:
    st.info(
        "AI ქულების სტატისტიკა გამოჩნდება მას შემდეგ, რაც გარიგებებზე შეფასების ქულები ჩაიწერება."
        if lang == "ka"
        else "AI score statistics will appear once trades have recorded AI scores."
    )
    return

  palette = _chart_palette()
  labels = _AI_CRITERIA_LABELS_KA if lang == "ka" else _AI_CRITERIA_LABELS_EN
  avg_total = ai_df["AI_Total"].mean()
  last_total = ai_df["AI_Total"].iloc[-1]
  prev_avg = ai_df["AI_Total"].iloc[:-1].mean() if len(ai_df) > 1 else None
  delta_str = f"{avg_total - prev_avg:+.2f} vs prev" if prev_avg is not None else None

  crit_means = {
      lbl: round(float(ai_df[key].mean()), 2)
      for lbl, key in zip(labels, _AI_CRITERIA_KEYS)
  }
  weakest_lbl = min(crit_means, key=crit_means.get)
  strongest_lbl = max(crit_means, key=crit_means.get)

  m_cols = st.columns(4)
  with m_cols[0]:
    with st.container(border=True):
      st.metric(
          "საშუალო AI ქულა" if lang == "ka" else "Avg AI Score",
          f"{avg_total:.2f} / 10",
          delta=delta_str,
          delta_color="normal",
      )
  with m_cols[1]:
    with st.container(border=True):
      st.metric(
          "ბოლო შეფასება" if lang == "ka" else "Latest Score",
          f"{last_total:.1f} / 10",
      )
  with m_cols[2]:
    with st.container(border=True):
      st.metric(
          "ყველაზე სუსტი კრიტერიუმი" if lang == "ka" else "Weakest Area",
          weakest_lbl,
          f"{crit_means[weakest_lbl]:.2f} / 2.00",
          delta_color="off",
      )
  with m_cols[3]:
    with st.container(border=True):
      st.metric(
          "ყველაზე ძლიერი კრიტერიუმი" if lang == "ka" else "Strongest Area",
          strongest_lbl,
          f"{crit_means[strongest_lbl]:.2f} / 2.00",
          delta_color="off",
      )

  c1, c2 = st.columns(2)
  with c1:
    st.caption(
        "საშუალო ქულა კრიტერიუმების მიხედვით (მაქს. 2.0)"
        if lang == "ka"
        else "Average score by criterion (max 2.0)"
    )
    crit_df = pd.DataFrame({
        "Criterion": list(crit_means.keys()),
        "Avg": list(crit_means.values()),
    })
    bar_chart = (
        alt.Chart(crit_df)
        .mark_bar(color=palette["ai_bar"], cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(
                "Criterion:N",
                sort=list(crit_means.keys()),
                title="Criterion",
                axis=alt.Axis(labelAngle=-25),
            ),
            y=alt.Y("Avg:Q", scale=alt.Scale(domain=[0, 2]), title="Avg"),
            tooltip=["Criterion", "Avg"],
        )
    )
    st.altair_chart(_apply_altair_theme(bar_chart, palette, 260), use_container_width=True)

  with c2:
    st.caption(
        "ჯამური AI ქულის დინამიკა (0–10)"
        if lang == "ka"
        else "Total AI score trend (0–10)"
    )
    trend_df = pd.DataFrame({
        "Index": list(range(1, len(ai_df) + 1)),
        "Score": ai_df["AI_Total"].tolist(),
    })
    line_chart = (
        alt.Chart(trend_df)
        .mark_line(
            color=palette["ai_line"],
            point=alt.OverlayMarkDef(color=palette["ai_line"], size=45),
            strokeWidth=2.5,
        )
        .encode(
            x=alt.X("Index:O", title="Index"),
            y=alt.Y("Score:Q", scale=alt.Scale(domain=[0, 10]), title="Score"),
            tooltip=["Index", "Score"],
        )
    )
    st.altair_chart(_apply_altair_theme(line_chart, palette, 260), use_container_width=True)


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
  )[[
      label,
      t("table_trade_count", lang),
      t("table_win_rate", lang),
      t("table_total_pnl", lang),
      t("table_avg_pnl", lang),
  ]]
  table[t("table_win_rate", lang)] = table[t("table_win_rate", lang)].round(0)
  _show_table(table, [t("table_total_pnl", lang), t("table_avg_pnl", lang)])


def _bar(g, key, value_col="Total", height=320):
  palette = _chart_palette()
  chart_df = g[[key, value_col]].copy()
  chart_df["Color"] = chart_df[value_col].apply(
      lambda v: palette["bar_pos"] if v >= 0 else palette["bar_neg"]
  )
  order_vals = chart_df[key].tolist()
  bars = (
      alt.Chart(chart_df)
      .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
      .encode(
          x=alt.X(f"{key}:N", sort=order_vals, title=key),
          y=alt.Y(f"{value_col}:Q", title=value_col),
          color=alt.Color("Color:N", scale=None, legend=None),
          tooltip=[key, value_col],
      )
  )
  st.altair_chart(_apply_altair_theme(bars, palette, height), use_container_width=True)


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
    _render_ai_scores_section(df, lang)
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

  idx = period_labels.index(selected_period)
  period = period_raw[idx]

  if period != "ყველა":
    trades = all_trades.tail(int(period.split()[1])).reset_index(drop=True)
  else:
    trades = all_trades

  s = _stats(trades)
  palette = _chart_palette()

  # ---- მთავარი ბარათები
  row1 = st.columns(4)
  with row1[0]:
    with st.container(border=True):
      st.metric(t("metric_total_pnl", lang), f"{s['total']:+.2f}$")
  with row1[1]:
    with st.container(border=True):
      st.metric(
          t("metric_win_rate", lang),
          f"{s['win_rate']:.1f}%",
          f"{s['wins']} / {s['losses']}",
          delta_color="off",
      )
  with row1[2]:
    with st.container(border=True):
      st.metric(t("metric_pf", lang), _fmt(s["pf"]))
  with row1[3]:
    with st.container(border=True):
      st.metric(
          t("metric_expectancy", lang),
          _fmt(s["expectancy"], "{:+.2f}", "$"),
      )

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
  x_col = t("equity_chart_x", lang)
  y_col = t("equity_chart_y", lang)
  equity = pd.DataFrame({
      x_col: list(range(1, len(trades) + 1)),
      y_col: trades["PnL"].cumsum().round(2).tolist(),
  })
  eq_color = palette["eq_pos"] if s["total"] >= 0 else palette["eq_neg"]
  area_chart = (
      alt.Chart(equity)
      .mark_area(
          line={"color": eq_color, "strokeWidth": 2.5},
          color=alt.Gradient(
              gradient="linear",
              stops=[
                  alt.GradientStop(color=eq_color, offset=0),
                  alt.GradientStop(color="rgba(34, 197, 94, 0.05)" if s["total"] >= 0 else "rgba(239, 68, 68, 0.05)", offset=1),
              ],
              x1=0,
              x2=0,
              y1=1,
              y2=0,
          ),
      )
      .encode(
          x=alt.X(f"{x_col}:Q", title=x_col),
          y=alt.Y(f"{y_col}:Q", title=y_col),
          tooltip=[x_col, y_col],
      )
  )
  st.altair_chart(_apply_altair_theme(area_chart, palette, 300), use_container_width=True)

  # ---- პერიოდების შედარება
  st.subheader(t("periods_comp_title", lang))
  comp = []
  for label, count in [
      (t("p_100", lang), 100),
      (t("p_50", lang), 50),
      (t("p_20", lang), 20),
      (t("p_10", lang), 10),
  ]:
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
    _show_table(
        pd.DataFrame(comp),
        [t("table_expectancy", lang), t("table_total_pnl", lang)],
    )

  st.divider()

  # ---- დეტალური ანალიზი ტაბებში
  tab_day, tab_pair, tab_pattern, tab_trigger, tab_side = st.tabs([
      t("tab_day_label", lang),
      t("tab_pair_label", lang),
      t("tab_pattern_label", lang),
      t("tab_trigger_label", lang),
      t("tab_side_label", lang),
  ])

  days_list = t("days_of_week", lang)

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

  # ---- AI ქულების სტატისტიკა
  _render_ai_scores_section(df, lang)
