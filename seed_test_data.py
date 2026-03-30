"""
Seed the admin account with realistic test accounts, holdings,
transactions, and historical snapshots for dashboard development.

Run with:  FLASK_ENV=development python seed_test_data.py
"""

import random
from datetime import date, timedelta
from flask_app import app, db
from flask_app.models import (
    User, Account, Holding, Allocation,
    Transaction, PortfolioSnapshot,
    ACTION_BUY, ACTION_SELL, ACTION_DIVIDEND, ACTION_REINVEST_DIVIDEND,
)

# ── Realistic prices (approximate, used only for cost-basis math) ──────────
TICKER_DATA = {
    # ticker: (approx_current_price, approx_avg_cost_per_share)
    "AAPL":  (213.0,  155.0),
    "MSFT":  (415.0,  270.0),
    "GOOGL": (175.0,  120.0),
    "AMZN":  (195.0,  140.0),
    "NVDA":  (875.0,  380.0),
    "META":  (520.0,  310.0),
    "VTI":   (270.0,  210.0),
    "VOO":   (495.0,  380.0),
    "BND":   ( 73.0,   76.0),
    "SCHD":  ( 82.0,   72.0),
    "QQQ":   (475.0,  350.0),
    "VIG":   (195.0,  165.0),
    "VXUS":  ( 62.0,   58.0),
    "T":     ( 17.0,   22.0),
    "VZ":    ( 40.0,   47.0),
    "JNJ":   (145.0,  155.0),
    "PG":    (170.0,  145.0),
    "KO":    ( 63.0,   58.0),
    "V":     (285.0,  220.0),
    "JPM":   (220.0,  165.0),
}

ACCOUNTS = [
    {
        "name":      "Schwab Brokerage",
        "brokerage": "Schwab",
        "tickers":   ["AAPL", "MSFT", "GOOGL", "NVDA", "V", "VOO", "QQQ"],
        "qtys":      [  85,     42,     60,     25,    50, 110,   35],
    },
    {
        "name":      "Fidelity Roth IRA",
        "brokerage": "Fidelity",
        "tickers":   ["VTI", "VXUS", "BND", "AMZN", "META"],
        "qtys":      [ 180,    95,   120,    30,    18],
    },
    {
        "name":      "Fidelity 401(k)",
        "brokerage": "Fidelity",
        "tickers":   ["VOO", "VIG", "SCHD", "BND"],
        "qtys":      [ 220,   85,    70,   150],
    },
    {
        "name":      "Schwab IRA",
        "brokerage": "Schwab",
        "tickers":   ["JPM", "JNJ", "PG", "KO", "T", "VZ", "MSFT"],
        "qtys":      [  40,   35,   45,  80,  200, 120,  28],
    },
]


def make_snapshots(account_id: int, tickers_and_qtys: list, days: int = 365):
    """Generate daily portfolio value snapshots going back `days` days."""
    snapshots = []
    base_date = date.today() - timedelta(days=days)

    # Build a simple daily value: drift each ticker price slightly each day
    prices = {t: TICKER_DATA[t][0] * random.uniform(0.60, 0.85) for t in [t for t, _ in tickers_and_qtys]}
    qtys   = {t: q for t, q in tickers_and_qtys}

    for i in range(days):
        snap_date = base_date + timedelta(days=i)
        # Skip weekends (rough approximation)
        if snap_date.weekday() >= 5:
            continue
        # Random walk: ±0.8% per day per ticker
        for ticker in prices:
            prices[ticker] *= (1 + random.uniform(-0.008, 0.009))

        total_mv = sum(prices[t] * qtys[t] for t in prices)
        total_cb = sum(TICKER_DATA[t][1] * qtys[t] for t in qtys)

        snapshots.append(PortfolioSnapshot(
            account_id         = account_id,
            snapshot_date      = snap_date,
            total_market_value = round(total_mv, 2),
            total_cost_basis   = round(total_cb, 2),
        ))
    return snapshots


def seed():
    with app.app_context():
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("ERROR: no 'admin' user found.")
            return

        # ── Wipe existing test accounts for admin ──────────────────────────
        existing = Account.query.filter_by(user_id=admin.id).all()
        for acct in existing:
            db.session.delete(acct)
        db.session.commit()
        print(f"Removed {len(existing)} existing account(s).")

        for pos, acct_def in enumerate(ACCOUNTS):
            # ── Create account ─────────────────────────────────────────────
            acct = Account(
                account_name = acct_def["name"],
                user_id      = admin.id,
                position     = pos,
                brokerage    = acct_def["brokerage"],
            )
            db.session.add(acct)
            db.session.flush()   # get acct.id

            tickers_and_qtys = list(zip(acct_def["tickers"], acct_def["qtys"]))

            # ── Holdings ───────────────────────────────────────────────────
            for ticker, qty in tickers_and_qtys:
                cost_per_share = TICKER_DATA[ticker][1] * random.uniform(0.92, 1.08)
                holding = Holding(
                    ticker     = ticker,
                    quantity   = qty,
                    account_id = acct.id,
                    cost_basis = round(cost_per_share * qty, 2),
                )
                db.session.add(holding)

            # ── Allocations ────────────────────────────────────────────────
            n = len(acct_def["tickers"])
            weights = [random.uniform(0.5, 2.0) for _ in range(n)]
            total_w = sum(weights)
            for ticker, w in zip(acct_def["tickers"], weights):
                alloc = Allocation(
                    name       = ticker,
                    target     = round(w / total_w * 100, 1),
                    account_id = acct.id,
                )
                db.session.add(alloc)

            # ── Transactions (last 18 months of buys + some dividends) ─────
            tx_date = date.today() - timedelta(days=548)
            for ticker, qty in tickers_and_qtys:
                price = TICKER_DATA[ticker][1] * random.uniform(0.88, 1.05)
                db.session.add(Transaction(
                    account_id  = acct.id,
                    date        = tx_date + timedelta(days=random.randint(0, 30)),
                    action_type = ACTION_BUY,
                    ticker      = ticker,
                    quantity    = qty,
                    price       = round(price, 4),
                    amount      = -round(price * qty, 2),
                    fees        = round(random.uniform(0, 4.99), 2),
                ))

            # A few dividend events for income tickers
            div_tickers = [t for t in acct_def["tickers"] if t in {"T","VZ","KO","SCHD","VIG","JNJ","PG","BND"}]
            for ticker in div_tickers:
                for q_offset in range(4):   # ~4 quarterly dividends
                    div_date = date.today() - timedelta(days=90 * (q_offset + 1))
                    div_amount = round(random.uniform(0.20, 1.10) * dict(tickers_and_qtys)[ticker], 2)
                    db.session.add(Transaction(
                        account_id  = acct.id,
                        date        = div_date,
                        action_type = ACTION_DIVIDEND,
                        ticker      = ticker,
                        quantity    = None,
                        price       = None,
                        amount      = div_amount,
                    ))

            # ── Historical snapshots ───────────────────────────────────────
            snaps = make_snapshots(acct.id, tickers_and_qtys, days=365)
            for s in snaps:
                db.session.add(s)

            print(f"  + {acct_def['name']}: {len(tickers_and_qtys)} holdings, {len(snaps)} snapshots")

        db.session.commit()
        print("\nDone. Reload the dashboard to see the data.")


if __name__ == '__main__':
    seed()
