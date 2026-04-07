#!/usr/bin/env python3
"""
take_daily_snapshot.py — Daily job: record today's portfolio value for all accounts.

Schedule this on PythonAnywhere as a daily task at 21:30 UTC (5:30 PM ET, after
market close) so it captures the day's closing prices:

    /home/chrisgig23/.virtualenvs/stockcalc-env/bin/python \
        /home/chrisgig23/stock-calc/take_daily_snapshot.py

The script creates one PortfolioSnapshot row per account per day.  If a snapshot
already exists for today it is skipped, so the script is safe to re-run.
"""

import os
import sys
from datetime import date

# ── Bootstrap Flask app context ───────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('FLASK_ENV', 'production')

from flask_app import app, db
from flask_app.models import Account, Holding, PortfolioSnapshot


def run():
    today = date.today()
    print(f"[Daily snapshot] Running for {today.isoformat()}.")

    with app.app_context():
        accounts = Account.query.all()

        if not accounts:
            print("[Daily snapshot] No accounts found.")
            return

        created = 0
        skipped = 0
        empty   = 0

        for account in accounts:
            # Skip if we already have today's snapshot for this account
            existing = PortfolioSnapshot.query.filter_by(
                account_id=account.id,
                snapshot_date=today,
            ).first()
            if existing:
                skipped += 1
                continue

            holdings = Holding.query.filter_by(account_id=account.id).all()
            total_mv = sum(h.market_value for h in holdings)
            total_cb = sum(h.cost_basis or 0.0 for h in holdings)

            if total_mv <= 0:
                empty += 1
                continue

            db.session.add(PortfolioSnapshot(
                account_id=account.id,
                snapshot_date=today,
                total_market_value=round(total_mv, 2),
                total_cost_basis=round(total_cb, 2) if total_cb > 0 else None,
            ))
            created += 1

        db.session.commit()
        print(
            f"[Daily snapshot] Done — {created} created, "
            f"{skipped} already existed, {empty} skipped (empty)."
        )


if __name__ == '__main__':
    run()
