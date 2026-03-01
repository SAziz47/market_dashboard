#!/usr/bin/env python3
"""
Market Dashboard Data Builder
Uses yf.Ticker().history() — same approach as traderwillhu's working script.
No session injection, no custom headers. Just works.

Usage:
    python scripts/build_data.py --out-dir data
    python scripts/build_data.py --out-dir data --symbols RELIANCE HDFCBANK TCS
"""

import argparse
import json
import sys
import time
import warnings
from datetime import datetime, timedelta, date
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    print("Missing dependencies. Run:  pip install -r requirements.txt")
    sys.exit(1)

# ── HOW LONG TO SLEEP BETWEEN REQUESTS ───────────────────────────────────────
# His script uses 0.15s. We use 0.3s to be slightly safer for 180 stocks.
SLEEP_BETWEEN = 0.3

# ── SECTORS & SYMBOLS ─────────────────────────────────────────────────────────
SECTORS = {
    "⚒️ Castings & Forgings": ["AIAENG","KALYANIFRG","NELCAST","STEELCAS","TIRUPATIFL"],
    "⚓ Port & Dredging": ["ADANIPORTS","ATL","DREDGECORP","GPPL","JSWINFRA"],
    "⚓ Shipping": ["GESHIP","SCI","SEAMECLTD","TRANSWORLD"],
    "⚗️ Commodity Chemicals": ["CHEMFAB","CHEMPLASTS","DEEPAKFERT","GHCL","GNFC","SRF","TATACHEM"],
    "⚙️ Abrasives & Bearings": ["CARBORUNIV","GRINDWELL","SKFINDIA","TIMKEN","WENDT"],
    "⚡ Heavy Electrical Equipment": ["ABB","BHEL","CGPOWER","ELECON","SIEMENS","SUZLON","THERMAX","VOLTAMP"],
    "✈️ Aerospace & Defense": ["ASTRAMICRO","AVANTEL","BDL","BEL","DATAPATTNS","GRSE","HAL","MIDHANI","MTARTECH"],
    "🏗️ Cement": ["ACC","AMBUJACEM","BIRLACORPN","DALBHARAT","GRASIM","JKCEMENT","SHREECEM","ULTRACEMCO"],
    "🏦 NBFC": ["BAJFINANCE","CHOLAFIN","IIFL","MANAPPURAM","MUTHOOTFIN","SHRIRAMFIN","SUNDARMFIN"],
    "🏦 Private Banks": ["AXISBANK","BANDHANBNK","FEDERALBNK","HDFCBANK","ICICIBANK","KOTAKBANK","YESBANK"],
    "🏛️ PSU Banks": ["BANKBARODA","BANKINDIA","CANBK","PNB","SBIN","UNIONBANK"],
    "💊 Pharmaceuticals": ["ABBOTINDIA","AUROPHARMA","BIOCON","CIPLA","DIVISLAB","DRREDDY","LUPIN","SUNPHARMA","ZYDUSLIFE"],
    "💻 IT Software": ["COFORGE","HCLTECH","INFY","LTIM","MPHASIS","PERSISTENT","TCS","TECHM","WIPRO"],
    "🏘️ Real Estate": ["BRIGADE","DLF","GODREJPROP","LODHA","OBEROIRLTY","PRESTIGE","SOBHA"],
    "🔋 Power Generation": ["ADANIGREEN","JSWENERGY","KPIGREEN","NHPC","NTPC","SJVN","TATAPOWER"],
    "🚗 Auto Components": ["BHARATFORG","BOSCHLTD","ENDURANCE","EXIDEIND","MOTHERSON","SCHAEFFLER","SONACOMS"],
    "🚲 2/3 Wheelers": ["BAJAJ-AUTO","EICHERMOT","HEROMOTOCO","TVSMOTOR"],
    "🚙 Passenger Cars": ["MARUTI","TATAMOTORS"],
    "🧪 Specialty Chemicals": ["AARTIIND","DEEPAKNTR","FINEORG","NAVINFLUOR","PIDILITIND","ROSSARI"],
    "🥫 Diversified FMCG": ["HINDUNILVR","ITC","VBL"],
    "🧴 Personal Care": ["BAJAJCON","COLPAL","DABUR","EMAMILTD","GODREJCP"],
    "🍪 Packaged Foods": ["BRITANNIA","NESTLEIND","ZYDUSWELL","BIKAJI"],
    "🎧 IT Enabled Services": ["CYIENT","LTTS","SASKEN","TATATECH","ZAGGLE"],
    "🛞 Tyres": ["APOLLOTYRE","BALKRISIND","CEATLTD","JKTYRE","MRF"],
    "📏 Iron & Steel Products": ["APLAPOLLO","JINDALSAW","RATNAMANI","WELCORP"],
    "🔧 Iron & Steel": ["JINDALSTEL","JSWSTEEL","SAIL","TATASTEEL"],
    "🔌 Household Appliances": ["AMBER","BAJAJELEC","BLUESTARCO","CROMPTON","HAVELLS","VOLTAS","WHIRLPOOL"],
    "💎 Gems & Jewellery": ["KALYANKJIL","RAJESHEXPO","SENCO","TITAN","VAIBHAVGBL"],
    "🏨 Hospitals": ["APOLLOHOSP","ASTERDM","FORTIS","MAXHEALTH","MEDANTA","NH"],
    "🛡️ Insurance": ["HDFCLIFE","ICICIPRULI","LICI","SBILIFE","ICICIGI","GICRE"],
    "📱 Telecom": ["BHARTIARTL","TATACOMM"],
    "🏬 Diversified Retail": ["DMART","SHOPERSTOP","TRENT","VMART"],
    "🚚 Logistics": ["BLUEDART","CONCOR","DELHIVERY","TCI","TCIEXP","VRLLOG"],
}

ALL_SYMBOLS      = list({sym for syms in SECTORS.values() for sym in syms})
SYMBOL_TO_SECTOR = {sym: sec for sec, syms in SECTORS.items() for sym in syms}

SPECIAL_TICKERS = {"BAJAJ-AUTO": "BAJAJ-AUTO.NS"}

def nse_ticker(sym):
    return SPECIAL_TICKERS.get(sym, f"{sym}.NS")

# ── SLOPE ─────────────────────────────────────────────────────────────────────

def slope_label(series):
    """Rising / flat / falling based on 5-day linear regression of the MA."""
    clean = series.dropna()
    if len(clean) < 5:
        return "unknown"
    recent = clean.iloc[-5:].values.astype(float)
    x = np.arange(len(recent))
    try:
        slope = np.polyfit(x, recent, 1)[0]
        pct   = slope / recent.mean() * 100
        if pct >  0.05: return "rising"
        if pct < -0.05: return "falling"
        return "flat"
    except Exception:
        return "unknown"

# ── FETCH ONE STOCK — exactly like traderwillhu ───────────────────────────────

def fetch_stock(sym, start_str, end_str):
    """
    Uses yf.Ticker().history() — the same call that works in the reference script.
    No session injection. No custom headers. yfinance handles auth internally.
    """
    ticker_str = nse_ticker(sym)
    try:
        ticker = yf.Ticker(ticker_str)

        # .history() with start/end — mirrors his `stock.history(period="60d")` pattern
        df = ticker.history(start=start_str, end=end_str)

        if df is None or df.empty or len(df) < 10:
            return None

        # yf.Ticker().history() returns a clean single-level DataFrame — no MultiIndex
        close  = df["Close"]
        volume = df["Volume"]
        price  = float(close.iloc[-1])

        # Moving averages
        ma50  = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()

        # Weekly close → 30W MA
        weekly = close.resample("W").last()
        ma30w  = weekly.rolling(30).mean()

        ma50_v  = float(ma50.iloc[-1])  if not pd.isna(ma50.iloc[-1])  else None
        ma200_v = float(ma200.iloc[-1]) if not pd.isna(ma200.iloc[-1]) else None
        ma30w_v = float(ma30w.iloc[-1]) if not pd.isna(ma30w.iloc[-1]) else None

        sl50  = slope_label(ma50)  if ma50_v  else "unknown"
        sl200 = slope_label(ma200) if ma200_v else "unknown"
        sl30w = slope_label(ma30w) if ma30w_v else "unknown"

        w52  = close.iloc[-252:] if len(close) >= 252 else close
        hi52 = float(w52.max())
        lo52 = float(w52.min())

        # Monthly volume — last 12 complete months
        monthly_vol = [
            {"month": idx.strftime("%b %Y"), "volume": int(v)}
            for idx, v in volume.resample("MS").sum().iloc[-13:-1].items()
        ]

        # Daily returns — last 252 days  (for Nifty-down-day analysis)
        daily_ret = close.pct_change().iloc[-252:]
        daily_returns = {
            str(d.date()): round(float(r) * 100, 3)
            for d, r in daily_ret.items() if not pd.isna(r)
        }

        # Historical closes — last 504 days  (for "above date X" screener)
        hist_prices = {
            str(d.date()): round(float(p), 2)
            for d, p in close.iloc[-504:].items() if not pd.isna(p)
        }

        return {
            "symbol":           sym,
            "sector":           SYMBOL_TO_SECTOR.get(sym, "Other"),
            "price":            round(price, 2),
            "ma50":             round(ma50_v, 2)  if ma50_v  else None,
            "ma200":            round(ma200_v, 2) if ma200_v else None,
            "ma30w":            round(ma30w_v, 2) if ma30w_v else None,
            "ma50Slope":        sl50,
            "ma200Slope":       sl200,
            "ma30wSlope":       sl30w,
            "high52w":          round(hi52, 2),
            "low52w":           round(lo52, 2),
            "aboveMa50":        bool(ma50_v  and price > ma50_v),
            "aboveMa200":       bool(ma200_v and price > ma200_v),
            "aboveRisingMa50":  bool(ma50_v  and price > ma50_v  and sl50  == "rising"),
            "aboveRisingMa30w": bool(ma30w_v and price > ma30w_v and sl30w == "rising"),
            "near52wHigh":      bool(price >= hi52 * 0.95),
            "near52wLow":       bool(price <= lo52 * 1.05),
            "monthlyVolume":    monthly_vol,
            "dailyReturns":     daily_returns,
            "historicalPrices": hist_prices,
        }

    except Exception as e:
        print(f"error: {e}")
        return None

# ── NIFTY INDEX — same pattern ────────────────────────────────────────────────

def fetch_nifty(start_str, end_str):
    """Fetch Nifty 500 daily returns using .history() just like reference script."""
    for sym in ["^CRSLDX", "^NSEI", "^BSESN"]:
        try:
            print(f"  Trying {sym}...", end="", flush=True)
            df = yf.Ticker(sym).history(start=start_str, end=end_str)
            if df is not None and not df.empty:
                ret = df["Close"].pct_change()
                result = {
                    str(d.date()): round(float(r) * 100, 3)
                    for d, r in ret.items() if not pd.isna(r)
                }
                print(f" ✓  ({len(result)} days)")
                return result
            print(" ✗ empty")
        except Exception as e:
            print(f" ✗ {e}")
        time.sleep(SLEEP_BETWEEN)

    print("  ⚠️  No index data available.")
    return {}

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--symbols", nargs="*", help="Subset of symbols for testing")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    end_date   = date.today()
    start_date = end_date - timedelta(days=800)
    start_str  = start_date.isoformat()
    end_str    = end_date.isoformat()

    symbols = args.symbols or ALL_SYMBOLS

    print("=" * 55)
    print("  ⚡ Market Radar — Data Builder")
    print(f"  Method  : yf.Ticker().history()  [no session injection]")
    print(f"  Stocks  : {len(symbols)}")
    print(f"  Period  : {start_str} → {end_str}")
    print(f"  Sleep   : {SLEEP_BETWEEN}s between requests")
    print("=" * 55)

    # Nifty index
    print("\n[1/3] Fetching Nifty index...")
    nifty_returns = fetch_nifty(start_str, end_str)
    big_down_days = sorted(
        [{"date": d, "return": r} for d, r in nifty_returns.items() if r <= -0.8],
        key=lambda x: x["return"]
    )
    print(f"       {len(big_down_days)} days with Nifty fall ≥ 0.8%")

    # All stocks
    print(f"\n[2/3] Fetching {len(symbols)} stocks...")
    stocks, skipped = [], []

    for i, sym in enumerate(symbols, 1):
        print(f"  [{i:3d}/{len(symbols)}] {sym:<18}", end="", flush=True)
        result = fetch_stock(sym, start_str, end_str)

        if result:
            stocks.append(result)
            print(f"✓  ₹{result['price']:>9,.2f}")
        else:
            print("✗  skip")
            skipped.append(sym)

        # Small sleep — same philosophy as reference script (0.15s), we use 0.3s
        if i < len(symbols):
            time.sleep(SLEEP_BETWEEN)

    # Sector breadth
    print(f"\n[3/3] Computing sector breadth...")
    breadth = {}
    for sec, syms in SECTORS.items():
        ss = [s for s in stocks if s["sector"] == sec]
        if ss:
            breadth[sec] = {
                "total":            len(ss),
                "aboveMa50":        sum(1 for s in ss if s["aboveMa50"]),
                "aboveMa200":       sum(1 for s in ss if s["aboveMa200"]),
                "aboveRisingMa50":  sum(1 for s in ss if s["aboveRisingMa50"]),
                "aboveRisingMa30w": sum(1 for s in ss if s["aboveRisingMa30w"]),
            }

    # Write outputs
    snap_path = out / "snapshot.json"
    with open(snap_path, "w") as f:
        json.dump({
            "stocks":          stocks,
            "sectorBreadth":   breadth,
            "nifty500Returns": nifty_returns,
            "bigDownDays":     big_down_days[:20],
        }, f, separators=(",", ":"))

    with open(out / "meta.json", "w") as f:
        json.dump({
            "updated":      datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "totalStocks":  len(stocks),
            "totalSkipped": len(skipped),
            "totalSectors": len(breadth),
            "dataStart":    start_str,
            "dataEnd":      end_str,
        }, f, indent=2)

    kb = snap_path.stat().st_size // 1024
    print(f"\n{'='*55}")
    print(f"  ✓ Fetched : {len(stocks)}")
    print(f"  ✗ Skipped : {len(skipped)}" +
          (f"  ({', '.join(skipped[:6])}{'…' if len(skipped) > 6 else ''})" if skipped else ""))
    print(f"  📄 {snap_path}  ({kb} KB)")
    print(f"{'='*55}")

    if not stocks:
        print("\n  ⚠️  0 stocks fetched.")
        print("  Fix: pip install --upgrade yfinance   then try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()
