# ⚡ Market Radar — Indian Equity Dashboard

Static Indian stock market dashboard with **daily auto-refresh via GitHub Actions** (Yahoo Finance / yfinance), hosted free on **GitHub Pages**. No API key required.

## Features

| Feature | Details |
|---|---|
| Stocks above 50 DMA / 200 DMA | Count + % breadth |
| Above 50 DMA with **rising slope** | Filters out flat/down MAs |
| Above rising **30-Week MA** | Weekly timeframe analysis |
| **Sister stock** movement | Type any symbol → see all sector peers |
| Stocks above **specific date price** | Enter any date, see which held up |
| **Nifty 500 down days** | Stocks that were UP when Nifty fell ≥ 0.8% |
| **TradingView chart** embed | Any NSE symbol, all timeframes |
| **52-week high/low** | Near high (≥95%) and near low (≤105%) |
| **Monthly volume** bar chart | Cumulative across all filtered stocks |
| Sector heatmap | Colour-coded breadth by industry |
| Full screener | Sort by any column, 5-star score, date filter |

Covers **300+ Indian stocks** across 35+ sectors (NSE).

---

## Quick Start (Local)

```bash
# 1. Clone / download this repo
git clone https://github.com/YOUR_USERNAME/market_dashboard.git
cd market_dashboard

# 2. Install dependencies (Python 3.9+)
pip install -r requirements.txt

# 3. Build data (fetches from Yahoo Finance — free, no API key)
python scripts/build_data.py --out-dir data

# 4. Preview in browser
python -m http.server 8000
# Open: http://localhost:8000
```

`build_data.py` generates:
- `data/snapshot.json` — all stock metrics, MA values, volumes, daily returns
- `data/meta.json` — timestamp and summary stats

---

## Deploy to GitHub Pages (Free hosting + daily auto-refresh)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/market_dashboard.git
git push -u origin main
```

### Step 2 — Generate initial data
Go to your repo → **Actions** tab → **"Refresh dashboard data"** → **Run workflow**

This fetches live data from Yahoo Finance and commits it to `data/`.

### Step 3 — Enable GitHub Pages
1. Go to repo **Settings → Pages**
2. Set Source to **GitHub Actions**
3. Save

### Step 4 — Done!
Your dashboard is live at:
```
https://YOUR_USERNAME.github.io/market_dashboard/
```

Data refreshes automatically **every weekday at 4:30 PM IST** (after NSE close).
You can also trigger manually from Actions at any time.

---

## Project Structure

```
market_dashboard/
├── .github/workflows/
│   └── refresh_data.yml      # Daily GitHub Actions workflow
├── scripts/
│   └── build_data.py         # Fetches yfinance data → JSON
├── data/                     # Auto-generated, committed by Actions
│   ├── snapshot.json         # All stock data (MAs, volumes, returns)
│   └── meta.json             # Last updated timestamp
├── index.html                # Dashboard frontend (pure HTML/CSS/JS)
├── requirements.txt
└── README.md
```

---

## Customise Your Stock List

Edit the `SECTORS` dict at the top of `scripts/build_data.py`:

```python
SECTORS = {
    "🚀 My Watchlist": ["RELIANCE", "HDFCBANK", "INFY"],
    # ... add more sectors
}
```

All NSE symbols are supported (they're fetched as `SYMBOL.NS` from Yahoo Finance).

---

## How It Works

1. **`build_data.py`** downloads 800 days of OHLCV data per stock via `yfinance`
2. Computes: 50 DMA, 200 DMA, 30-week MA, slope direction, 52W high/low, monthly volumes, daily returns
3. Fetches **Nifty 500 index** (`^CRSLDX`) to identify significant down days
4. Outputs everything to `data/snapshot.json`
5. **`index.html`** fetches the JSON and renders 7 interactive tabs — no framework, no build step

---

## Data Source

Yahoo Finance via [yfinance](https://github.com/ranaroussi/yfinance) — free, no registration, no API key needed.

> Data is typically delayed 15 minutes. For EOD analysis this is sufficient.
