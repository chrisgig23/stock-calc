"""
price_cache.py — In-process price cache for yfinance lookups.

Stores fetched prices in a module-level dict with a 15-minute TTL.
This prevents hammering Yahoo Finance on every page load and avoids
429 rate-limit errors on PythonAnywhere's shared IPs.

Usage:
    from flask_app.utils.price_cache import get_price, get_prices

    price  = get_price('AAPL')
    prices = get_prices(['AAPL', 'MSFT', 'VOO'])
"""

import yfinance as yf
from datetime import datetime

# { ticker: (price: float, fetched_at: datetime) }
_cache: dict = {}

CACHE_TTL_SECONDS = 900   # 15 minutes


def get_price(ticker: str) -> float:
    """Return the current price for a ticker, using cached value if fresh."""
    now = datetime.utcnow()
    entry = _cache.get(ticker)
    if entry:
        price, fetched_at = entry
        if (now - fetched_at).total_seconds() < CACHE_TTL_SECONDS:
            return price

    try:
        info = yf.Ticker(ticker).info
        price = (
            info.get('currentPrice')
            or info.get('regularMarketPreviousClose')
            or info.get('navPrice')
            or info.get('open')
            or 0.0
        )
        price = float(price)
    except Exception:
        price = 0.0

    _cache[ticker] = (price, now)
    return price


def get_prices(tickers: list) -> dict:
    """Return {ticker: price} for all tickers, using cache where available."""
    return {t: get_price(t) for t in tickers}


def bust_cache(ticker: str = None) -> None:
    """Evict one ticker (or clear everything) from the cache."""
    if ticker:
        _cache.pop(ticker, None)
    else:
        _cache.clear()
