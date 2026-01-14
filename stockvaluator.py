import time
import random
import pickle
from pathlib import Path
from functools import lru_cache

import yfinance as yf
import pandas as pd

CACHE_DIR = Path("stock_cache")
CACHE_DIR.mkdir(exist_ok=True)

RATE_LIMIT_RANGE = (0.8, 1.4)  # Sekunden
CACHE_TTL_HOURS = 24


def _sleep():
    time.sleep(random.uniform(*RATE_LIMIT_RANGE))


def _is_cache_valid(path: Path) -> bool:
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    return age_hours < CACHE_TTL_HOURS


class StockDataLoader:
    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache

    def _cache_path(self, ticker: str) -> Path:
        return CACHE_DIR / f"{ticker.upper()}.pkl"

    def load(self, ticker: str) -> dict | None:
        ticker = ticker.upper()
        cache_path = self._cache_path(ticker)

        # ---- Cache ----
        if self.use_cache and cache_path.exists() and _is_cache_valid(cache_path):
            return pickle.load(open(cache_path, "rb"))

        _sleep()

        try:
            stock = yf.Ticker(ticker)

            # ⚠️ ALLES NUR EINMAL LADEN
            info = stock.info
            financials = stock.financials
            quarterly = stock.quarterly_financials
            balance = stock.balance_sheet
            estimates = stock.earnings_estimate

            data = {
                "info": info,
                "financials": financials,
                "quarterly": quarterly,
                "balance": balance,
                "estimates": estimates,
            }

            if self.use_cache:
                pickle.dump(data, open(cache_path, "wb"))

            return data

        except Exception as e:
            print(f"[WARN] {ticker}: {e}")
            return None


def calculate_cagr(start, end, years):
    if start is None or end is None or start <= 0:
        return None
    return ((end / start) ** (1 / years)) - 1


def safe_get(df, row, idx=0):
    try:
        val = df.loc[row].iloc[idx]
        return float(val) if pd.notna(val) else None
    except Exception:
        return None


class StockAnalyzer:
    def analyze(self, ticker: str, raw: dict) -> dict:
        info = raw["info"]
        fin = raw["financials"]
        q = raw["quarterly"]
        bal = raw["balance"]
        est = raw["estimates"]

        kgv = info.get("trailingPE") or info.get("forwardPE")
        eps_now = safe_get(fin, "Diluted EPS", 0)
        eps_1y = safe_get(fin, "Diluted EPS", 1)
        eps_3y = safe_get(fin, "Diluted EPS", 3)

        gw_fy = (
            ((eps_now / eps_1y) - 1) * 100
            if eps_now and eps_1y and eps_1y != 0
            else None
        )

        long_gw = (
            calculate_cagr(eps_3y, eps_now, 3) * 100 if eps_3y and eps_now else None
        )

        peg = (
            kgv / gw_fy if kgv and gw_fy and gw_fy > 0 else info.get("trailingPegRatio")
        )

        return {
            "Ticker": ticker,
            "KGV": round(kgv, 2) if kgv else None,
            "GW_FY_%": round(gw_fy, 2) if gw_fy else None,
            "Long_GW_%": round(long_gw, 2) if long_gw else None,
            "PEG": round(peg, 2) if peg else None,
        }


def analyze_stocks(tickers):
    loader = StockDataLoader(use_cache=True)
    analyzer = StockAnalyzer()

    results = []

    for t in tickers:
        raw = loader.load(t)
        if raw:
            results.append(analyzer.analyze(t, raw))

    return pd.DataFrame(results)


tickers = ["SAP"]
df = analyze_stocks(tickers)
print(df)
