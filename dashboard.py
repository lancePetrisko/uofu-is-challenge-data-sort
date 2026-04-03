"""
Coffee Cart Analytics Dashboard
UofU IS Analytics Competition — Spring 2026
Run with: streamlit run dashboard.py
"""

import math
import random
import statistics
import sys
import os
from collections import defaultdict

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Pull data loading + aggregation from the analysis script
sys.path.insert(0, os.path.dirname(__file__))
from analyze_coffee import (
    load_data, build_aggregations, pearson_r,
    TIMESLOT_HOURS, DOW_ORDER, SEASONS, T_CRIT_95, DATA_FILE
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BRAND_COLORS = {
    "Latte":         "#7B4F2E",
    "Americano":     "#3D2B1F",
    "Cappuccino":    "#C08457",
    "Iced Coffee":   "#6BA3BE",
    "Cold Brew":     "#2C5F7A",
    "Hot Chocolate": "#A0522D",
    "Iced Tea":      "#8DB48E",
}
SEASON_COLORS = {
    "Winter": "#7EB3D8",
    "Spring": "#82C882",
    "Summer": "#F4A935",
    "Fall":   "#D2622A",
}
CHART_BG  = "rgba(0,0,0,0)"
FONT_FAM  = "Inter, sans-serif"
CARD_CSS  = """
<style>
  [data-testid="stMetric"] {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 16px 20px;
  }
  [data-testid="stMetricLabel"] { font-size: 0.78rem; color: #a6adc8; }
  [data-testid="stMetricValue"] { font-size: 1.6rem; color: #cdd6f4; }
  [data-testid="stMetricDelta"] { font-size: 0.75rem; }
  .stTabs [data-baseweb="tab-list"] { gap: 8px; }
  .stTabs [data-baseweb="tab"] {
    background: #1e1e2e;
    border-radius: 8px 8px 0 0;
    padding: 8px 18px;
    color: #a6adc8;
  }
  .stTabs [aria-selected="true"] {
    background: #313244 !important;
    color: #cdd6f4 !important;
  }
  h1, h2, h3 { color: #cdd6f4; }
  .insight-box {
    background: #1e1e2e;
    border-left: 3px solid #89b4fa;
    border-radius: 0 8px 8px 0;
    padding: 12px 16px;
    margin: 8px 0 16px 0;
    color: #cdd6f4;
    font-size: 0.9rem;
  }
</style>
"""

def insight(text):
    st.markdown(f'<div class="insight-box">💡 {text}</div>', unsafe_allow_html=True)

def plotly_defaults(fig, title=None):
    fig.update_layout(
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family=FONT_FAM, color="#cdd6f4", size=12),
        margin=dict(l=10, r=10, t=40 if title else 10, b=10),
        title=dict(text=title, font=dict(size=15, color="#cdd6f4")) if title else None,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#a6adc8")),
    )
    fig.update_xaxes(gridcolor="#313244", linecolor="#45475a", tickfont=dict(color="#a6adc8"))
    fig.update_yaxes(gridcolor="#313244", linecolor="#45475a", tickfont=dict(color="#a6adc8"))
    return fig


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading data…")
def get_aggregations():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, DATA_FILE)
    traffic_rows, sales_rows = load_data(path)
    agg = build_aggregations(sales_rows, traffic_rows)

    # Convert defaultdicts to plain dicts for Streamlit cache serialisation
    def to_dict(d):
        if isinstance(d, defaultdict):
            return {k: to_dict(v) for k, v in d.items()}
        return d

    return {k: to_dict(v) for k, v in agg.items()}, len(sales_rows), len(traffic_rows)


# ---------------------------------------------------------------------------
# Derived helpers
# ---------------------------------------------------------------------------
def hour_averages(agg):
    hr = agg["hour_revenue"]
    hd = agg["hour_day_set"]
    return {h: hr[h] / len(hd[h]) for h in hr if hd[h]}

def dow_averages(agg):
    dr = agg["dow_revenue"]
    dd = agg["dow_day_set"]
    return {d: dr[d] / len(dd[d]) for d in dr if dd[d]}


# ===========================================================================
# PAGE LAYOUT
# ===========================================================================

st.set_page_config(
    page_title="Coffee Cart Analytics",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CARD_CSS, unsafe_allow_html=True)

# Header
st.markdown("## ☕ Coffee Cart Analytics Dashboard")
st.markdown("*UofU IS Analytics Competition — Spring 2026 · Mar 2024 – Mar 2025*")
st.divider()

# Load
agg, n_sales, n_traffic = get_aggregations()
daily_sales  = agg["daily_sales"]
daily_list   = sorted(daily_sales.values())
total_rev    = sum(daily_sales.values())
n_days       = len(daily_sales)
mean_rev     = statistics.mean(daily_list)

# KPI row
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue",      f"${total_rev:,.0f}")
k2.metric("Trading Days",       f"{n_days}")
k3.metric("Total Transactions", f"{n_sales:,}")
k4.metric("Avg Daily Revenue",  f"${mean_rev:,.2f}")
k5.metric("Avg Txns/Day",       f"{n_sales/n_days:.0f}")

st.divider()

# Tabs
tabs = st.tabs([
    "📈 Demand Patterns",
    "🥤 Drink Popularity",
    "🌡️ Weather",
    "🚶 Foot Traffic",
    "⚙️ Strategy",
    "📊 Confidence Interval",
    "⏱️ Best 4-Hour Window",
])


# ===========================================================================
# TAB 1 — DEMAND PATTERNS
# ===========================================================================
with tabs[0]:
    st.subheader("Q1 · When Is Coffee Demand Highest?")
    c1, c2 = st.columns(2)

    # Hourly bar
    with c1:
        h_avgs = hour_averages(agg)
        hours  = list(range(7, 21))
        revs   = [h_avgs.get(h, 0) for h in hours]
        colors = ["#89b4fa" if r == max(revs) else "#585b70" for r in revs]
        fig = go.Figure(go.Bar(
            x=[f"{h}:00" for h in hours],
            y=revs,
            marker_color=colors,
            text=[f"${r:.0f}" for r in revs],
            textposition="outside",
            textfont=dict(size=10),
        ))
        plotly_defaults(fig, "Avg Revenue per Day by Hour")
        fig.update_yaxes(title_text="$ / day")
        st.plotly_chart(fig, width='stretch')
        insight("Hours 7–13 are consistently strong (~$63–66/day). Revenue drops sharply at 2pm, with 6–8pm earning only ~38% of peak.")

    # Day-of-week bar
    with c2:
        d_avgs = dow_averages(agg)
        days   = DOW_ORDER
        revs2  = [d_avgs.get(d, 0) for d in days]
        colors2 = ["#f38ba8" if d in ("Monday", "Sunday") else "#a6e3a1" for d in days]
        fig2 = go.Figure(go.Bar(
            x=days,
            y=revs2,
            marker_color=colors2,
            text=[f"${r:.0f}" for r in revs2],
            textposition="outside",
            textfont=dict(size=10),
        ))
        plotly_defaults(fig2, "Avg Revenue per Day by Day of Week")
        fig2.update_yaxes(title_text="$ / day")
        st.plotly_chart(fig2, width='stretch')
        insight("Wednesday peaks at $843/day. Monday is 56% lower at $369 — likely reduced campus activity at week-start.")

    # Seasonal
    st.subheader("Seasonal Demand")
    date_to_season = agg["date_to_season"]
    season_days_set = defaultdict(set)
    for date, s in date_to_season.items():
        season_days_set[s].add(date)
    season_txn = agg["season_txn_count"]

    seasons   = SEASONS
    txns      = [season_txn[s] for s in seasons]
    uniq_days = [len(season_days_set[s]) for s in seasons]
    tpd       = [t / d if d else 0 for t, d in zip(txns, uniq_days)]

    c3, c4 = st.columns(2)
    with c3:
        fig3 = go.Figure(go.Bar(
            x=seasons, y=txns,
            marker_color=[SEASON_COLORS[s] for s in seasons],
            text=txns, textposition="outside",
        ))
        plotly_defaults(fig3, "Total Transactions by Season")
        st.plotly_chart(fig3, width='stretch')

    with c4:
        fig4 = go.Figure(go.Bar(
            x=seasons, y=tpd,
            marker_color=[SEASON_COLORS[s] for s in seasons],
            text=[f"{v:.1f}" for v in tpd], textposition="outside",
        ))
        plotly_defaults(fig4, "Avg Transactions per Day by Season")
        fig4.update_yaxes(title_text="transactions / day")
        st.plotly_chart(fig4, width='stretch')
        insight("Fall leads in daily transaction rate (105/day). Summer is weakest (90/day) — campus is less populated over summer break.")


# ===========================================================================
# TAB 2 — DRINK POPULARITY
# ===========================================================================
with tabs[1]:
    st.subheader("Q2 · What Drinks Are Most Popular?")

    item_season_qty = agg["item_season_qty"]
    item_season_rev = agg["item_season_rev"]
    drink_temp_season = agg["drink_temp_season"]
    season_txn = agg["season_txn_count"]

    all_items = list(item_season_qty.keys())
    item_totals = {it: sum(item_season_qty[it].values()) for it in all_items}
    item_rev_totals = {it: sum(item_season_rev[it].values()) for it in all_items}
    ranked = sorted(all_items, key=item_totals.get, reverse=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        fig = go.Figure(go.Pie(
            labels=ranked,
            values=[item_totals[i] for i in ranked],
            hole=0.45,
            marker_colors=[BRAND_COLORS[i] for i in ranked],
            textinfo="label+percent",
            textfont=dict(size=12),
        ))
        plotly_defaults(fig, "Overall Sales Share by Item")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, width='stretch')

    with c2:
        # Revenue bar
        fig2 = go.Figure(go.Bar(
            x=[item_rev_totals[i] for i in ranked],
            y=ranked,
            orientation="h",
            marker_color=[BRAND_COLORS[i] for i in ranked],
            text=[f"${item_rev_totals[i]:,.0f}" for i in ranked],
            textposition="outside",
        ))
        plotly_defaults(fig2, "Total Revenue by Item")
        fig2.update_xaxes(title_text="Total Revenue ($)")
        fig2.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig2, width='stretch')

    insight("Latte leads in both volume (24.1%) and revenue ($61,495). Despite low quantity, Cold Brew punches above its weight in revenue at $43,885 — it's the highest-priced item at $5.50.")

    # Stacked bar: items by season
    st.subheader("Item Mix by Season")
    records = []
    for item in ranked:
        for season in SEASONS:
            records.append({
                "Item": item,
                "Season": season,
                "Qty": item_season_qty[item].get(season, 0),
            })

    fig3 = go.Figure()
    for item in ranked:
        fig3.add_trace(go.Bar(
            name=item,
            x=SEASONS,
            y=[item_season_qty[item].get(s, 0) for s in SEASONS],
            marker_color=BRAND_COLORS[item],
        ))
    fig3.update_layout(barmode="stack")
    plotly_defaults(fig3, "Item Volume by Season (Stacked)")
    fig3.update_yaxes(title_text="Transactions")
    st.plotly_chart(fig3, width='stretch')

    # Hot/Cold shift
    st.subheader("Hot vs Cold Preference by Season")
    c3, c4 = st.columns(2)
    with c3:
        hot_pcts  = []
        cold_pcts = []
        for s in SEASONS:
            hot  = drink_temp_season.get("Hot", {}).get(s, 0)
            cold = drink_temp_season.get("Cold", {}).get(s, 0)
            total = hot + cold
            hot_pcts.append(hot / total * 100 if total else 0)
            cold_pcts.append(cold / total * 100 if total else 0)

        fig4 = go.Figure()
        fig4.add_trace(go.Bar(name="Hot", x=SEASONS, y=hot_pcts,
                              marker_color="#f38ba8", text=[f"{v:.0f}%" for v in hot_pcts],
                              textposition="inside"))
        fig4.add_trace(go.Bar(name="Cold", x=SEASONS, y=cold_pcts,
                              marker_color="#89dceb", text=[f"{v:.0f}%" for v in cold_pcts],
                              textposition="inside"))
        fig4.update_layout(barmode="stack")
        plotly_defaults(fig4, "Hot vs Cold Share by Season (%)")
        fig4.update_yaxes(title_text="%", range=[0, 105])
        st.plotly_chart(fig4, width='stretch')
        insight("Cold drinks jump from 22% in Winter to 44% in Summer. Menu promotion should shift accordingly.")

    with c4:
        # Seasonal revenue share heatmap
        season_totals = {s: sum(item_season_rev[it].get(s, 0) for it in all_items) for s in SEASONS}
        z = [[item_season_rev[it].get(s, 0) / season_totals[s] * 100 if season_totals[s] else 0
              for s in SEASONS]
             for it in ranked]

        fig5 = go.Figure(go.Heatmap(
            z=z,
            x=SEASONS,
            y=ranked,
            colorscale="YlOrBr",
            text=[[f"{v:.1f}%" for v in row] for row in z],
            texttemplate="%{text}",
            showscale=True,
            colorbar=dict(tickfont=dict(color="#a6adc8")),
        ))
        plotly_defaults(fig5, "Revenue Share (%) per Season")
        fig5.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig5, width='stretch')


# ===========================================================================
# TAB 3 — WEATHER
# ===========================================================================
with tabs[2]:
    st.subheader("Q3 · How Does Weather Influence Consumption?")

    daily_temp  = agg["daily_temp"]
    daily_hot   = agg["daily_hot_count"]
    daily_cold  = agg["daily_cold_count"]
    daily_txn   = agg["daily_txn_count"]
    weather_sales = agg["weather_type_sales"]

    # Build per-day scatter data
    scatter_dates = [d for d in daily_temp
                     if (daily_hot.get(d, 0) + daily_cold.get(d, 0)) > 0]
    temps_s  = [daily_temp[d] for d in scatter_dates]
    cold_rat = [daily_cold[d] / (daily_hot[d] + daily_cold[d]) * 100
                for d in scatter_dates]
    seasons_s = [agg["date_to_season"].get(d, "Unknown") for d in scatter_dates]

    r_val = pearson_r(temps_s, cold_rat)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.scatter(
            x=temps_s, y=cold_rat,
            color=seasons_s,
            color_discrete_map=SEASON_COLORS,
            labels={"x": "Daily Temperature (°F)", "y": "Cold Drink Ratio (%)"},
            trendline="ols",
            trendline_color_override="#f38ba8",
        )
        plotly_defaults(fig, f"Temperature vs Cold Drink Ratio  (r = {r_val:.3f})")
        fig.update_traces(marker=dict(size=5, opacity=0.6))
        st.plotly_chart(fig, width='stretch')
        insight(f"Pearson r = {r_val:.3f} — strong positive correlation. Warmer days reliably drive cold drink demand. Temperature does NOT affect total volume (r = -0.13).")

    with c2:
        # Temp bucket bars
        buckets = [
            ("< 20°F",  lambda t: t < 20),
            ("20–39°F", lambda t: 20 <= t < 40),
            ("40–54°F", lambda t: 40 <= t < 55),
            ("55–69°F", lambda t: 55 <= t < 70),
            ("70–84°F", lambda t: 70 <= t < 85),
            ("≥ 85°F",  lambda t: t >= 85),
        ]
        labels, avg_txns, avg_colds, day_counts = [], [], [], []
        for label, fn in buckets:
            bd = [d for d in daily_temp if fn(daily_temp[d])]
            if not bd:
                continue
            labels.append(label)
            day_counts.append(len(bd))
            avg_txns.append(statistics.mean(daily_txn[d] for d in bd))
            avg_colds.append(statistics.mean(
                daily_cold[d] / (daily_hot[d] + daily_cold[d]) * 100
                for d in bd if (daily_hot[d] + daily_cold[d]) > 0
            ))

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(
            name="Avg Txns/Day", x=labels, y=avg_txns,
            marker_color="#89b4fa",
            text=[f"{v:.0f}" for v in avg_txns], textposition="outside",
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            name="Cold Ratio %", x=labels, y=avg_colds,
            mode="lines+markers",
            line=dict(color="#89dceb", width=2),
            marker=dict(size=8),
        ), secondary_y=True)
        plotly_defaults(fig2, "Temperature Buckets: Volume & Cold Ratio")
        fig2.update_yaxes(title_text="Avg Txns/Day", secondary_y=False, gridcolor="#313244")
        fig2.update_yaxes(title_text="Cold Drink %", secondary_y=True, showgrid=False)
        st.plotly_chart(fig2, width='stretch')

    # Weather type
    st.subheader("Weather Type vs Transaction Value")
    wt_labels = sorted(weather_sales, key=lambda x: len(weather_sales[x]), reverse=True)
    wt_means  = [statistics.mean(weather_sales[wt]) for wt in wt_labels]
    wt_counts = [len(weather_sales[wt]) for wt in wt_labels]

    c3, c4 = st.columns(2)
    with c3:
        fig3 = go.Figure(go.Bar(
            x=wt_labels, y=wt_counts,
            marker_color=["#89b4fa", "#a6adc8", "#74c7ec", "#b4befe"],
            text=wt_counts, textposition="outside",
        ))
        plotly_defaults(fig3, "Transactions by Weather Type")
        fig3.update_yaxes(title_text="Transaction Count")
        st.plotly_chart(fig3, width='stretch')

    with c4:
        fig4 = go.Figure(go.Bar(
            x=wt_labels, y=wt_means,
            marker_color=["#89b4fa", "#a6adc8", "#74c7ec", "#b4befe"],
            text=[f"${v:.4f}" for v in wt_means], textposition="outside",
        ))
        plotly_defaults(fig4, "Mean Transaction Value by Weather Type")
        fig4.update_yaxes(title_text="Mean $ per Transaction", range=[min(wt_means)*0.98, max(wt_means)*1.02])
        st.plotly_chart(fig4, width='stretch')
        insight("Rain slightly boosts per-transaction value ($7.12 vs $7.08 avg). Weather type has minimal impact on purchase amount — customers buy regardless of conditions.")


# ===========================================================================
# TAB 4 — FOOT TRAFFIC
# ===========================================================================
with tabs[3]:
    st.subheader("Q4 · Foot Traffic vs Sales Relationship")

    hour_rev_by_date  = agg["hour_rev_by_date"]
    traffic_by_slot   = agg["traffic_by_date_slot"]

    traffic_vals, txn_vals, slot_labels, season_labels = [], [], [], []
    slot_bucket = defaultdict(lambda: {"traffic": [], "txn": []})

    for key, traffic in traffic_by_slot.items():
        date, slot = key
        slot_hours = TIMESLOT_HOURS.get(slot, set())
        slot_rev   = sum(hour_rev_by_date.get(date, {}).get(h, 0.0) for h in slot_hours)
        slot_txn   = round(slot_rev / 4.75) if slot_rev > 0 else 0

        traffic_vals.append(traffic)
        txn_vals.append(slot_txn)
        slot_labels.append(slot)
        season_labels.append(agg["date_to_season"].get(date, "Unknown"))
        slot_bucket[slot]["traffic"].append(traffic)
        slot_bucket[slot]["txn"].append(slot_txn)

    r = pearson_r(traffic_vals, txn_vals)

    c1, c2 = st.columns(2)
    with c1:
        slot_colors = {"Morning": "#f9e2af", "Midday": "#a6e3a1",
                       "Afternoon": "#89b4fa", "Evening": "#cba6f7"}
        fig = px.scatter(
            x=traffic_vals, y=txn_vals,
            color=slot_labels,
            color_discrete_map=slot_colors,
            labels={"x": "Estimated Foot Traffic", "y": "Estimated Transactions"},
            opacity=0.5,
            trendline="ols",
            trendline_scope="overall",
            trendline_color_override="#f38ba8",
        )
        plotly_defaults(fig, f"Foot Traffic vs Slot Transactions  (r = {r:.3f})")
        fig.update_traces(marker=dict(size=4))
        st.plotly_chart(fig, width='stretch')
        insight(f"r = {r:.3f} — moderate positive correlation. Foot traffic is a reliable signal but other factors (day-of-week, season) also drive sales.")

    with c2:
        slots = ["Morning", "Midday", "Afternoon", "Evening"]
        avg_tr  = [statistics.mean(slot_bucket[s]["traffic"]) if slot_bucket[s]["traffic"] else 0 for s in slots]
        avg_tx  = [statistics.mean(slot_bucket[s]["txn"]) if slot_bucket[s]["txn"] else 0 for s in slots]
        conv    = [tx / tr * 100 if tr > 0 else 0 for tx, tr in zip(avg_tx, avg_tr)]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2.add_trace(go.Bar(
            name="Avg Traffic", x=slots, y=avg_tr,
            marker_color="#585b70", text=[f"{v:.0f}" for v in avg_tr], textposition="inside",
        ), secondary_y=False)
        fig2.add_trace(go.Scatter(
            name="Conversion %", x=slots, y=conv,
            mode="lines+markers+text",
            line=dict(color="#f9e2af", width=2),
            marker=dict(size=10),
            text=[f"{v:.1f}%" for v in conv],
            textposition="top center",
        ), secondary_y=True)
        plotly_defaults(fig2, "Avg Traffic & Conversion Rate by Timeslot")
        fig2.update_yaxes(title_text="Avg Foot Traffic", secondary_y=False, gridcolor="#313244")
        fig2.update_yaxes(title_text="Conversion %", secondary_y=True, showgrid=False)
        st.plotly_chart(fig2, width='stretch')
        insight("Evening converts best (17%) despite low absolute traffic — loyal regulars. Morning converts 14.8%. Midday has highest traffic but modest conversion (8.4%).")


# ===========================================================================
# TAB 5 — STRATEGY
# ===========================================================================
with tabs[4]:
    st.subheader("Q5 · What Operating Strategy Is Most Efficient?")

    hour_revenue = agg["hour_revenue"]
    hour_day_set = agg["hour_day_set"]
    dow_revenue  = agg["dow_revenue"]
    dow_day_set  = agg["dow_day_set"]

    h_avgs = hour_averages(agg)
    d_avgs = dow_averages(agg)
    peak_h = max(h_avgs.values())
    peak_d = max(d_avgs.values())

    c1, c2 = st.columns(2)
    with c1:
        hours  = list(range(7, 21))
        revs   = [h_avgs.get(h, 0) for h in hours]
        colors = ["#a6e3a1" if r >= peak_h * 0.60 else "#f38ba8" for r in revs]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=[f"{h}:00" for h in hours], y=revs,
            marker_color=colors,
            name="Revenue",
        ))
        fig.add_hline(y=peak_h * 0.60, line_dash="dash",
                      line_color="#f9e2af", annotation_text="60% threshold",
                      annotation_font_color="#f9e2af")
        plotly_defaults(fig, "Revenue Efficiency by Hour (green = keep, red = cut)")
        fig.update_yaxes(title_text="Avg $ / day")
        st.plotly_chart(fig, width='stretch')
        insight("Hours 18–20 fall below 40% of peak. Closing at 6pm saves ~3 staff-hours/day with minimal revenue loss (~$74/day).")

    with c2:
        days   = DOW_ORDER
        revs2  = [d_avgs.get(d, 0) for d in days]
        colors2 = ["#a6e3a1" if r >= peak_d * 0.55 else "#f38ba8" for r in revs2]
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=days, y=revs2, marker_color=colors2, name="Revenue",
        ))
        fig2.add_hline(y=peak_d * 0.55, line_dash="dash",
                       line_color="#f9e2af", annotation_text="55% threshold",
                       annotation_font_color="#f9e2af")
        plotly_defaults(fig2, "Revenue by Day of Week (green = full staff, red = reduce)")
        fig2.update_yaxes(title_text="Avg $ / day")
        st.plotly_chart(fig2, width='stretch')
        insight("Monday ($369) and Sunday ($435) are well below threshold. Reduce staffing or delay opening on these days.")

    # Menu heatmap
    st.subheader("Seasonal Menu Mix — Revenue Share Heatmap")
    item_season_rev = agg["item_season_rev"]
    all_items = list(item_season_rev.keys())
    ranked    = sorted(all_items, key=lambda x: sum(item_season_rev[x].values()), reverse=True)
    season_totals = {s: sum(item_season_rev[it].get(s, 0) for it in all_items) for s in SEASONS}
    z = [[item_season_rev[it].get(s, 0) / season_totals[s] * 100 if season_totals[s] else 0
          for s in SEASONS]
         for it in ranked]

    fig3 = go.Figure(go.Heatmap(
        z=z, x=SEASONS, y=ranked,
        colorscale="YlOrBr",
        text=[[f"{v:.1f}%" for v in row] for row in z],
        texttemplate="%{text}", textfont={"size": 13},
        showscale=True,
        colorbar=dict(tickfont=dict(color="#a6adc8")),
    ))
    plotly_defaults(fig3, "Item Revenue Share (%) by Season — Prioritize darker cells each season")
    fig3.update_layout(yaxis=dict(autorange="reversed"), height=320)
    st.plotly_chart(fig3, width='stretch')
    insight("Iced Tea never exceeds 2.6% in any season — consider replacing it with a more popular item. Hot Chocolate drops from 10.4% in Winter to 4.7% in Summer — promote only in cold months.")


# ===========================================================================
# TAB 6 — CONFIDENCE INTERVAL
# ===========================================================================
with tabs[5]:
    st.subheader("Q6 · Expected Range for Average Daily Sales (95% CI)")

    n         = len(daily_list)
    mean_s    = statistics.mean(daily_list)
    std_s     = statistics.stdev(daily_list)
    se        = std_s / math.sqrt(n)
    ci_lo     = mean_s - T_CRIT_95 * se
    ci_hi     = mean_s + T_CRIT_95 * se

    # Bootstrap
    random.seed(42)
    boot_means = sorted(
        statistics.mean(random.choices(daily_list, k=n))
        for _ in range(10_000)
    )
    b_lo = boot_means[250]
    b_hi = boot_means[9750]

    # KPIs
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mean Daily Revenue", f"${mean_s:,.2f}")
    m2.metric("Std Deviation",      f"${std_s:,.2f}")
    m3.metric("Standard Error",     f"${se:,.2f}")
    m4.metric("95% CI Width",       f"±${(ci_hi-ci_lo)/2:,.2f}")

    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        # Histogram with CI shading
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=daily_list, nbinsx=35,
            marker_color="#89b4fa", opacity=0.7,
            name="Daily Sales",
        ))
        fig.add_vline(x=mean_s, line_color="#a6e3a1", line_width=2,
                      annotation_text=f"Mean ${mean_s:.0f}", annotation_font_color="#a6e3a1")
        fig.add_vrect(x0=ci_lo, x1=ci_hi, fillcolor="#f38ba8",
                      opacity=0.15, line_width=0, annotation_text="95% CI",
                      annotation_font_color="#f38ba8")
        fig.add_vline(x=ci_lo, line_color="#f38ba8", line_dash="dash", line_width=1)
        fig.add_vline(x=ci_hi, line_color="#f38ba8", line_dash="dash", line_width=1)
        plotly_defaults(fig, "Distribution of Daily Sales with 95% CI")
        fig.update_xaxes(title_text="Daily Revenue ($)")
        fig.update_yaxes(title_text="# Days")
        st.plotly_chart(fig, width='stretch')

    with c2:
        # Bootstrap distribution
        sample_size = min(2000, len(boot_means))
        step = len(boot_means) // sample_size
        boot_sample = boot_means[::step]

        fig2 = go.Figure()
        fig2.add_trace(go.Histogram(
            x=boot_sample, nbinsx=60,
            marker_color="#cba6f7", opacity=0.8,
            name="Bootstrap Means",
        ))
        fig2.add_vline(x=b_lo, line_color="#f38ba8", line_dash="dash",
                       annotation_text=f"${b_lo:.0f}", annotation_font_color="#f38ba8")
        fig2.add_vline(x=b_hi, line_color="#f38ba8", line_dash="dash",
                       annotation_text=f"${b_hi:.0f}", annotation_font_color="#f38ba8")
        fig2.add_vrect(x0=b_lo, x1=b_hi, fillcolor="#f38ba8", opacity=0.15, line_width=0)
        plotly_defaults(fig2, "Bootstrap Distribution of Sample Means (10,000 resamples)")
        fig2.update_xaxes(title_text="Resampled Mean ($)")
        fig2.update_yaxes(title_text="Frequency")
        st.plotly_chart(fig2, width='stretch')

    # Summary table
    st.subheader("CI Summary")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
| Method | Lower Bound | Upper Bound |
|---|---|---|
| **t-distribution** | ${ci_lo:,.2f} | ${ci_hi:,.2f} |
| **Bootstrap** | ${b_lo:,.2f} | ${b_hi:,.2f} |
""")
    with col_b:
        insight(f"We are 95% confident average daily sales fall between **${ci_lo:,.2f}** and **${ci_hi:,.2f}**. Bootstrap validation nearly matches — confirming the estimate is robust.")


# ===========================================================================
# TAB 7 — 4-HOUR WINDOW
# ===========================================================================
with tabs[6]:
    st.subheader("Q7 (Bonus) · Optimal 4-Hour Operating Window")

    hour_rev_by_date = agg["hour_rev_by_date"]
    date_to_season   = agg["date_to_season"]

    start_hours = list(range(7, 18))

    window_total = defaultdict(float)
    window_count = defaultdict(int)
    season_win_total = defaultdict(lambda: defaultdict(float))
    season_win_count = defaultdict(lambda: defaultdict(int))
    wday_total = defaultdict(float); wday_count = defaultdict(int)
    wend_total = defaultdict(float); wend_count = defaultdict(int)

    for date, hours_dict in hour_rev_by_date.items():
        season = date_to_season.get(date, "Unknown")
        is_wend = date.weekday() >= 5
        for start in start_hours:
            rev = sum(hours_dict.get(h, 0.0) for h in range(start, start + 4))
            window_total[start] += rev; window_count[start] += 1
            season_win_total[season][start] += rev; season_win_count[season][start] += 1
            if is_wend:
                wend_total[start] += rev; wend_count[start] += 1
            else:
                wday_total[start] += rev; wday_count[start] += 1

    window_avgs = {s: window_total[s] / window_count[s] for s in start_hours if window_count[s]}
    ranked_w = sorted(start_hours, key=window_avgs.get, reverse=True)

    c1, c2 = st.columns(2)
    with c1:
        labels  = [f"{s}:00–{s+3}:59" for s in ranked_w]
        avgs    = [window_avgs[s] for s in ranked_w]
        colors  = ["#a6e3a1" if i == 0 else "#585b70" for i in range(len(ranked_w))]

        fig = go.Figure(go.Bar(
            x=avgs, y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"${v:.2f}" for v in avgs],
            textposition="outside",
        ))
        plotly_defaults(fig, "All 4-Hour Windows — Avg Daily Revenue (Overall)")
        fig.update_xaxes(title_text="Avg Revenue ($)")
        fig.update_layout(yaxis=dict(autorange="reversed"), height=440)
        st.plotly_chart(fig, width='stretch')
        best = ranked_w[0]
        insight(f"Best overall: **{best}:00–{best+3}:59** at ${window_avgs[best]:.2f}/day. The top 4 windows are within $11 of each other — morning hours are reliably strong.")

    with c2:
        # By season
        fig2 = go.Figure()
        for season in SEASONS:
            s_avgs = [season_win_total[season][s] / season_win_count[season][s]
                      if season_win_count[season][s] else 0
                      for s in start_hours]
            fig2.add_trace(go.Scatter(
                x=[f"{s}:00" for s in start_hours],
                y=s_avgs,
                name=season,
                mode="lines+markers",
                line=dict(color=SEASON_COLORS[season], width=2),
                marker=dict(size=7),
            ))
        plotly_defaults(fig2, "4-Hour Window Revenue by Season")
        fig2.update_yaxes(title_text="Avg Revenue ($)")
        fig2.update_xaxes(title_text="Window Start Hour")
        st.plotly_chart(fig2, width='stretch')
        insight("Summer's curve peaks at 10am, while all other seasons peak at 7am. Adjust opening strategy in summer to capitalize on mid-morning traffic.")

    # Weekday vs weekend
    st.subheader("Weekday vs Weekend Window Comparison")
    c3, c4 = st.columns(2)
    for col, (label, tot_d, cnt_d) in zip([c3, c4], [
        ("Weekday", wday_total, wday_count),
        ("Weekend", wend_total, wend_count),
    ]):
        with col:
            avgs2 = [tot_d[s] / cnt_d[s] if cnt_d[s] else 0 for s in start_hours]
            best2 = start_hours[avgs2.index(max(avgs2))]
            colors2 = ["#a6e3a1" if s == best2 else "#585b70" for s in start_hours]
            fig3 = go.Figure(go.Bar(
                x=[f"{s}:00–{s+3}:59" for s in start_hours],
                y=avgs2,
                marker_color=colors2,
                text=[f"${v:.0f}" for v in avgs2],
                textposition="outside",
            ))
            plotly_defaults(fig3, f"{label} — Best: {best2}:00–{best2+3}:59 (${max(avgs2):.2f}/day)")
            fig3.update_xaxes(tickangle=45)
            fig3.update_yaxes(title_text="Avg Revenue ($)")
            st.plotly_chart(fig3, width='stretch')


# Footer
st.divider()
st.markdown(
    "<p style='color:#585b70; font-size:0.8rem; text-align:center;'>"
    "Data: 34,521 transactions · 355 trading days · Mar 2024 – Mar 2025 · "
    "Built with Streamlit + Plotly · No pandas"
    "</p>",
    unsafe_allow_html=True,
)
