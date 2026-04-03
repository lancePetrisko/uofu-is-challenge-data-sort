# ☕ Coffee Cart Analytics Dashboard

An interactive web analytics dashboard built for the **University of Utah IS Analytics Competition — Spring 2026**. Analyzes a full year of simulated coffee cart transaction data (34,521 transactions across 355 trading days) to answer 7 business case questions and deliver data-driven operational recommendations.

---

## 📊 Live Dashboard Preview

The dashboard features 7 analysis tabs with 20+ interactive charts:

| Tab | What's Inside |
|---|---|
| 📈 Demand Patterns | Hourly revenue bars, day-of-week breakdown, seasonal transaction trends |
| 🥤 Drink Popularity | Sales donut, revenue ranking, stacked seasonal mix, hot/cold shift heatmap |
| 🌡️ Weather | Temperature vs cold-drink scatter (r = 0.783), bucket analysis, weather type breakdown |
| 🚶 Foot Traffic | Traffic vs sales scatter with trendline, timeslot conversion rates |
| ⚙️ Strategy | Color-coded hour/day efficiency charts, seasonal menu mix heatmap |
| 📊 Confidence Interval | Daily sales histogram with CI band, bootstrap validation (10,000 resamples) |
| ⏱️ Best 4-Hour Window | Ranked window bar chart, season-by-season curves, overall winner badge |

---

## 🗂️ Project Structure

```
├── app.py                  # Flask backend — processes data & serves JSON API
├── analyze_coffee.py       # Core data loading, aggregation, and statistics engine
├── templates/
│   └── index.html          # Single-page dashboard (Chart.js + vanilla CSS/JS)
├── 2010_coffee_cart_data 2026 (1).xlsx   # Source data (2 sheets, 34,521 rows)
└── IS 2010 Analytics Competition - Business Case (1).pdf
```

---

## 🚀 Getting Started

### 1. Install dependencies

```bash
pip3 install flask openpyxl statsmodels
```

### 2. Run the app

```bash
python3 app.py
```

### 3. Open in browser

```
http://localhost:5000
```

> The app processes the Excel file on startup (~3–5 seconds), then serves all data instantly via a local API.

---

## 🔬 Analysis & Key Findings

### Q1 — When is demand highest?
- **Peak hours:** 7am–1pm (~$63–66/day per hour); sharp drop-off after 2pm
- **Peak day:** Wednesday ($843/day avg); Monday is the weakest ($369/day)
- **Peak season:** Fall (105 transactions/day); Summer is slowest (90/day)

### Q2 — What drinks are most popular?
- **#1 overall:** Latte (24.1% of volume, $61,495 total revenue)
- **Summer shift:** Cold Brew + Iced Coffee jump to 42.5% of summer revenue (vs 21% in Winter)
- **Weakest item:** Iced Tea — never exceeds 2.6% share in any season

### Q3 — How does weather influence sales?
- **Strong correlation** between daily temperature and cold drink demand: **r = 0.783**
- Temperature has **no effect on total volume** (r = −0.13) — customers buy regardless
- Rain marginally boosts mean transaction value ($7.12 vs $7.08 baseline)

### Q4 — Foot traffic vs sales?
- **Moderate positive correlation:** r = 0.525 between estimated foot traffic and slot transactions
- Evening converts best (**17.1%**) despite low absolute traffic — loyal regulars
- Midday has the highest raw traffic but only 8.4% conversion

### Q5 — Optimal operating strategy?
- **Hours:** Operate 7am–5pm core; hours 6–8pm earn only ~38% of morning peak
- **Days:** Full staffing Tue–Sat; reduce Mon/Sun (both ≥44% below Wednesday peak)
- **Menu:** Push Cold Brew & Iced Coffee in Summer/Spring; Hot Chocolate is Winter-only; discontinue Iced Tea promotion

### Q6 — Average daily sales confidence interval
- **95% CI (t-distribution):** $658.49 – $718.21
- **Bootstrap validation (10,000 resamples):** $658.24 – $718.67 ✓
- Based on n = 355 days, mean = $688.35, σ = $286.11

### Q7 — Best 4-hour operating window
- **Overall winner:** 7:00–10:59am at **$254.77/day avg**
- **Summer exception:** 10:00am–1:59pm peaks at $241.85/day — open later in warmer months

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Data processing | Python 3 — `openpyxl`, `statistics`, `collections`, `math`, `random` |
| Backend | Flask 3 |
| Frontend | Vanilla HTML/CSS/JS |
| Charts | Chart.js 4 |
| Theme | Catppuccin Mocha (dark) |

> **No pandas** used anywhere in the data pipeline.

---

## 📁 Data Overview

| Sheet | Rows | Description |
|---|---|---|
| Estimated Campus Foot Traffic | 1,464 | Daily foot traffic by timeslot (Morning / Midday / Afternoon / Evening) |
| Historic Sales + Weather | 34,521 | Transactions with item, price, date/time, weather, and season |

**Date range:** March 1, 2024 – March 1, 2025  
**Menu:** Latte $5.00 · Americano $4.00 · Cappuccino $5.00 · Hot Chocolate $4.25 · Iced Coffee $4.50 · Cold Brew $5.50 · Iced Tea $4.50

---

## 👤 Author

Developed and maintained by **[Lance Petrisko](https://www.linkedin.com/in/lance-petrisko-b9994036a/)**
