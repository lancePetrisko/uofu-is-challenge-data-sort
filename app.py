"""
Coffee Cart Analytics — Flask Web App
Run: python3 app.py
Opens at: http://localhost:5000
"""

import json
import math
import os
import random
import statistics
import sys
from collections import defaultdict

from flask import Flask, jsonify, render_template

sys.path.insert(0, os.path.dirname(__file__))
from analyze_coffee import (
    load_data, build_aggregations, pearson_r,
    TIMESLOT_HOURS, DOW_ORDER, SEASONS, T_CRIT_95, DATA_FILE,
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Build all data once at startup
# ---------------------------------------------------------------------------

def _to_plain(d):
    """Recursively convert defaultdicts/sets to plain dicts/lists."""
    if isinstance(d, defaultdict):
        return {k: _to_plain(v) for k, v in d.items()}
    if isinstance(d, dict):
        return {k: _to_plain(v) for k, v in d.items()}
    if isinstance(d, set):
        return list(d)
    return d


def build_payload():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(script_dir, DATA_FILE)
    traffic_rows, sales_rows = load_data(path)
    agg = build_aggregations(sales_rows, traffic_rows)

    daily_sales   = agg["daily_sales"]
    daily_list    = sorted(daily_sales.values())
    n_days        = len(daily_sales)
    n_txns        = len(sales_rows)
    total_rev     = sum(daily_sales.values())
    mean_rev      = statistics.mean(daily_list)
    std_rev       = statistics.stdev(daily_list)

    # ── Q1: Demand ──────────────────────────────────────────────────────────
    hour_revenue = agg["hour_revenue"]
    hour_day_set = agg["hour_day_set"]
    hour_avgs = {
        str(h): round(hour_revenue[h] / len(hour_day_set[h]), 2)
        for h in hour_revenue if hour_day_set[h]
    }

    dow_revenue = agg["dow_revenue"]
    dow_day_set = agg["dow_day_set"]
    dow_avgs = {
        d: round(dow_revenue[d] / len(dow_day_set[d]), 2)
        for d in DOW_ORDER if dow_day_set[d]
    }

    date_to_season = agg["date_to_season"]
    season_days_set = defaultdict(set)
    for date, s in date_to_season.items():
        season_days_set[s].add(date)
    season_txn = agg["season_txn_count"]
    season_demand = {
        s: {
            "txns": season_txn[s],
            "days": len(season_days_set[s]),
            "tpd":  round(season_txn[s] / len(season_days_set[s]), 1) if season_days_set[s] else 0,
        }
        for s in SEASONS
    }

    # ── Q2: Drinks ──────────────────────────────────────────────────────────
    item_season_qty = agg["item_season_qty"]
    item_season_rev = agg["item_season_rev"]
    drink_temp_season = agg["drink_temp_season"]

    all_items = list(item_season_qty.keys())
    item_totals = {it: sum(item_season_qty[it].values()) for it in all_items}
    item_rev_totals = {it: sum(item_season_rev[it].values()) for it in all_items}
    ranked_items = sorted(all_items, key=item_totals.get, reverse=True)

    season_totals_rev = {
        s: sum(item_season_rev[it].get(s, 0) for it in all_items)
        for s in SEASONS
    }
    menu_heatmap = {
        it: {
            s: round(item_season_rev[it].get(s, 0) / season_totals_rev[s] * 100, 1)
            if season_totals_rev[s] else 0
            for s in SEASONS
        }
        for it in ranked_items
    }

    hot_cold_by_season = {}
    for s in SEASONS:
        hot  = drink_temp_season.get("Hot",  {}).get(s, 0)
        cold = drink_temp_season.get("Cold", {}).get(s, 0)
        total = hot + cold
        hot_cold_by_season[s] = {
            "hot":  round(hot  / total * 100, 1) if total else 0,
            "cold": round(cold / total * 100, 1) if total else 0,
        }

    # ── Q3: Weather ─────────────────────────────────────────────────────────
    daily_temp  = agg["daily_temp"]
    daily_hot   = agg["daily_hot_count"]
    daily_cold  = agg["daily_cold_count"]
    daily_txn   = agg["daily_txn_count"]
    weather_sales = agg["weather_type_sales"]

    scatter_dates = [
        d for d in daily_temp
        if (daily_hot.get(d, 0) + daily_cold.get(d, 0)) > 0
    ]
    scatter_data = [
        {
            "temp":   round(daily_temp[d], 1),
            "cold":   round(daily_cold[d] / (daily_hot[d] + daily_cold[d]) * 100, 1),
            "season": date_to_season.get(d, "Unknown"),
            "txns":   daily_txn[d],
        }
        for d in scatter_dates
    ]
    r_temp_cold = round(pearson_r(
        [daily_temp[d] for d in scatter_dates],
        [daily_cold[d] / (daily_hot[d] + daily_cold[d]) for d in scatter_dates],
    ), 3)

    bucket_defs = [
        ("< 20°F",  lambda t: t < 20),
        ("20–39°F", lambda t: 20 <= t < 40),
        ("40–54°F", lambda t: 40 <= t < 55),
        ("55–69°F", lambda t: 55 <= t < 70),
        ("70–84°F", lambda t: 70 <= t < 85),
        ("≥ 85°F",  lambda t: t >= 85),
    ]
    temp_buckets = []
    for label, fn in bucket_defs:
        bd = [d for d in daily_temp if fn(daily_temp[d])]
        if not bd:
            continue
        avg_cold = statistics.mean(
            daily_cold[d] / (daily_hot[d] + daily_cold[d]) * 100
            for d in bd if (daily_hot[d] + daily_cold[d]) > 0
        )
        temp_buckets.append({
            "label":    label,
            "days":     len(bd),
            "avg_txns": round(statistics.mean(daily_txn[d] for d in bd), 1),
            "avg_cold": round(avg_cold, 1),
        })

    weather_type_stats = [
        {
            "type":  wt,
            "count": len(weather_sales[wt]),
            "mean":  round(statistics.mean(weather_sales[wt]), 4),
        }
        for wt in sorted(weather_sales, key=lambda x: len(weather_sales[x]), reverse=True)
    ]

    # ── Q4: Foot Traffic ────────────────────────────────────────────────────
    hour_rev_by_date = agg["hour_rev_by_date"]
    traffic_by_slot  = agg["traffic_by_date_slot"]

    foot_scatter = []
    slot_bucket  = defaultdict(lambda: {"traffic": [], "txn": []})
    for (date, slot), traffic in traffic_by_slot.items():
        slot_hours = TIMESLOT_HOURS.get(slot, set())
        slot_rev   = sum(hour_rev_by_date.get(date, {}).get(h, 0.0) for h in slot_hours)
        slot_txn   = round(slot_rev / 4.75) if slot_rev > 0 else 0
        foot_scatter.append({"traffic": traffic, "txns": slot_txn, "slot": slot})
        slot_bucket[slot]["traffic"].append(traffic)
        slot_bucket[slot]["txn"].append(slot_txn)

    r_foot = round(pearson_r(
        [p["traffic"] for p in foot_scatter],
        [p["txns"]    for p in foot_scatter],
    ), 3)
    slot_conversion = [
        {
            "slot":      s,
            "avg_tr":    round(statistics.mean(slot_bucket[s]["traffic"]), 1) if slot_bucket[s]["traffic"] else 0,
            "avg_txn":   round(statistics.mean(slot_bucket[s]["txn"]),     1) if slot_bucket[s]["txn"]     else 0,
            "conv_pct":  round(
                statistics.mean(slot_bucket[s]["txn"]) /
                statistics.mean(slot_bucket[s]["traffic"]) * 100, 2
            ) if slot_bucket[s]["traffic"] else 0,
        }
        for s in ["Morning", "Midday", "Afternoon", "Evening"]
    ]

    # ── Q6: Confidence Interval ─────────────────────────────────────────────
    n   = len(daily_list)
    se  = std_rev / math.sqrt(n)
    ci_lo = round(mean_rev - T_CRIT_95 * se, 2)
    ci_hi = round(mean_rev + T_CRIT_95 * se, 2)
    random.seed(42)
    boot_means = sorted(
        statistics.mean(random.choices(daily_list, k=n))
        for _ in range(10_000)
    )
    b_lo = round(boot_means[250], 2)
    b_hi = round(boot_means[9750], 2)

    # ── Q7: 4-Hour Window ───────────────────────────────────────────────────
    start_hours = list(range(7, 18))
    win_total = defaultdict(float)
    win_count = defaultdict(int)
    season_win = defaultdict(lambda: defaultdict(float))
    season_win_cnt = defaultdict(lambda: defaultdict(int))

    for date, hours_dict in hour_rev_by_date.items():
        season = date_to_season.get(date, "Unknown")
        for start in start_hours:
            rev = sum(hours_dict.get(h, 0.0) for h in range(start, start + 4))
            win_total[start] += rev
            win_count[start] += 1
            season_win[season][start] += rev
            season_win_cnt[season][start] += 1

    window_avgs = sorted(
        [
            {
                "label": f"{s}:00–{s+3}:59",
                "start": s,
                "avg":   round(win_total[s] / win_count[s], 2),
            }
            for s in start_hours if win_count[s]
        ],
        key=lambda x: x["avg"],
        reverse=True,
    )
    season_best_window = {
        s: max(
            start_hours,
            key=lambda h: season_win[s][h] / season_win_cnt[s][h] if season_win_cnt[s][h] else 0,
        )
        for s in SEASONS
    }
    season_window_curves = {
        s: [
            {
                "start": h,
                "label": f"{h}:00",
                "avg":   round(season_win[s][h] / season_win_cnt[s][h], 2) if season_win_cnt[s][h] else 0,
            }
            for h in start_hours
        ]
        for s in SEASONS
    }

    return {
        "kpis": {
            "total_revenue": round(total_rev, 2),
            "n_days":        n_days,
            "n_txns":        n_txns,
            "mean_rev":      round(mean_rev, 2),
            "avg_tpd":       round(n_txns / n_days, 1),
        },
        "demand": {
            "hour_avgs":     hour_avgs,
            "dow_avgs":      dow_avgs,
            "season_demand": season_demand,
        },
        "drinks": {
            "ranked_items":    ranked_items,
            "item_totals":     item_totals,
            "item_rev_totals": item_rev_totals,
            "item_season_qty": {it: dict(item_season_qty[it]) for it in all_items},
            "menu_heatmap":    menu_heatmap,
            "hot_cold":        hot_cold_by_season,
        },
        "weather": {
            "scatter":       scatter_data,
            "r":             r_temp_cold,
            "temp_buckets":  temp_buckets,
            "weather_types": weather_type_stats,
        },
        "traffic": {
            "scatter":    foot_scatter,
            "r":          r_foot,
            "conversion": slot_conversion,
        },
        "ci": {
            "n":        n,
            "mean":     round(mean_rev, 2),
            "std":      round(std_rev,  2),
            "se":       round(se,       2),
            "t_crit":   T_CRIT_95,
            "ci_lo":    ci_lo,
            "ci_hi":    ci_hi,
            "b_lo":     b_lo,
            "b_hi":     b_hi,
            "daily_list": [round(v, 2) for v in daily_list],
        },
        "window": {
            "ranked":         window_avgs,
            "season_best":    {s: f"{season_best_window[s]}:00–{season_best_window[s]+3}:59" for s in SEASONS},
            "season_curves":  season_window_curves,
        },
        "seasons": SEASONS,
        "items":   ranked_items,
    }


print("Loading and processing data…")
DATA = build_payload()
print("Ready.")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    return jsonify(DATA)


if __name__ == "__main__":
    app.run(debug=False, port=5000)
