from flask import Blueprint, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account, Holding, Transaction, PortfolioSnapshot
from datetime import datetime, date
from collections import defaultdict
import yfinance as yf

market_bp = Blueprint('market', __name__)


@market_bp.route('/refresh_market_data/<int:account_id>', methods=['GET'])
@login_required
def refresh_market_data(account_id):
    """Touches last_updated on all holdings so the UI shows a fresh timestamp.
    Prices are fetched live from yfinance on each page load — no DB caching."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    now = datetime.utcnow()
    Holding.query.filter_by(account_id=account_id).update({'last_updated': now})
    db.session.commit()
    flash('Market data refreshed.', 'success')
    return redirect(url_for('portfolio.view_positions', account_id=account_id))


# ---------------------------------------------------------------------------
# Daily Snapshot  — call once per day (e.g. via scheduled task)
# Records today's live portfolio value for each account.
# ---------------------------------------------------------------------------

@market_bp.route('/snapshot/today', methods=['POST'])
@login_required
def snapshot_today():
    """Create a portfolio snapshot for today for all of the current user's accounts."""
    today = date.today()
    created = 0

    for account in current_user.get_accounts():
        existing = PortfolioSnapshot.query.filter_by(
            account_id=account.id,
            snapshot_date=today,
        ).first()
        if existing:
            continue  # already have today's snapshot

        total_mv = sum(h.market_value for h in account.holdings)
        total_cb = sum(h.cost_basis or 0.0 for h in account.holdings)

        if total_mv <= 0:
            continue

        db.session.add(PortfolioSnapshot(
            account_id=account.id,
            snapshot_date=today,
            total_market_value=round(total_mv, 2),
            total_cost_basis=round(total_cb, 2) if total_cb > 0 else None,
        ))
        created += 1

    db.session.commit()
    flash(f'Snapshot saved for today ({created} account{"s" if created != 1 else ""} updated).', 'success')
    return redirect(url_for('main.dashboard'))


# ---------------------------------------------------------------------------
# Historical Backfill  — one-time operation to seed the growth chart
# Replays transaction history day-by-day, fetches historical close prices
# from yfinance, and inserts PortfolioSnapshot rows for each transaction date.
# ---------------------------------------------------------------------------

@market_bp.route('/snapshot/backfill', methods=['POST'])
@login_required
def snapshot_backfill():
    """
    Backfill portfolio snapshots from transaction history.

    Algorithm per account:
      1. Sort all transactions chronologically.
      2. For each unique transaction date, update a running portfolio state
         (ticker → quantity, ticker → cost_basis).
      3. Fetch yfinance historical close prices for every ticker over the
         full date range in one call per ticker.
      4. Value the portfolio at each date using the closest available close.
      5. Write a PortfolioSnapshot row (skip dates that already exist).
    """
    total_created = 0
    errors = []

    for account in current_user.get_accounts():
        txns = (Transaction.query
                .filter_by(account_id=account.id)
                .order_by(Transaction.date.asc())
                .all())

        if not txns:
            continue

        # All tickers that appear in transactions
        tickers = list({t.ticker for t in txns if t.ticker})
        if not tickers:
            continue

        start_date = txns[0].date
        end_date   = date.today()

        # ── Fetch historical close prices once per ticker ──────────────────
        price_history = {}   # ticker -> sorted list of (date, price)
        price_map     = {}   # ticker -> {date: price}

        for ticker in tickers:
            try:
                hist = yf.Ticker(ticker).history(
                    start=start_date.isoformat(),
                    end=end_date.isoformat(),
                    auto_adjust=True,
                )
                daily = {}
                for idx, row in hist.iterrows():
                    d = idx.date() if hasattr(idx, 'date') else idx
                    daily[d] = float(row['Close'])
                price_map[ticker]     = daily
                price_history[ticker] = sorted(daily.keys())
            except Exception as exc:
                errors.append(f"{ticker}: {exc}")
                price_map[ticker]     = {}
                price_history[ticker] = []

        # ── Group transactions by date ─────────────────────────────────────
        txns_by_date = defaultdict(list)
        for t in txns:
            txns_by_date[t.date].append(t)

        # ── Walk forward through dates, maintaining running holdings ───────
        holdings   = defaultdict(float)   # ticker -> total shares
        cost_basis = defaultdict(float)   # ticker -> total cost basis

        def nearest_price(ticker, d):
            """Return the closest historical close price on or before date d."""
            daily  = price_map.get(ticker, {})
            dates  = price_history.get(ticker, [])
            if not dates:
                return None
            price = daily.get(d)
            if price is not None:
                return price
            # binary search for latest date <= d
            lo, hi = 0, len(dates) - 1
            result = None
            while lo <= hi:
                mid = (lo + hi) // 2
                if dates[mid] <= d:
                    result = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            return daily[dates[result]] if result is not None else None

        for txn_date in sorted(txns_by_date.keys()):
            # Apply this day's transactions
            for t in txns_by_date[txn_date]:
                if not t.ticker:
                    continue
                qty = t.quantity or 0.0
                amt = abs(t.amount) if t.amount else 0.0

                if t.action_type in ('buy', 'reinvest_shares', 'reinvest_dividend'):
                    holdings[t.ticker]   += qty
                    cost_basis[t.ticker] += amt
                elif t.action_type == 'sell':
                    cur = holdings[t.ticker]
                    if cur > 0 and qty > 0:
                        ratio = min(qty / cur, 1.0)
                        cost_basis[t.ticker] *= (1.0 - ratio)
                    holdings[t.ticker] = max(0.0, cur - qty)

            if not any(v > 0 for v in holdings.values()):
                continue

            # Skip if snapshot already exists for this account+date
            if PortfolioSnapshot.query.filter_by(
                    account_id=account.id,
                    snapshot_date=txn_date).first():
                continue

            # Value the portfolio at txn_date
            total_mv = 0.0
            total_cb = sum(v for v in cost_basis.values())
            for ticker, qty in holdings.items():
                if qty <= 0:
                    continue
                price = nearest_price(ticker, txn_date)
                if price:
                    total_mv += qty * price

            if total_mv <= 0:
                continue

            db.session.add(PortfolioSnapshot(
                account_id=account.id,
                snapshot_date=txn_date,
                total_market_value=round(total_mv, 2),
                total_cost_basis=round(total_cb, 2) if total_cb > 0 else None,
            ))
            total_created += 1

    db.session.commit()

    if errors:
        flash(f'Backfill complete — {total_created} snapshots created '
              f'({len(errors)} ticker error{"s" if len(errors) != 1 else ""}). '
              f'Some tickers may have limited history.', 'warning')
    else:
        flash(f'Backfill complete — {total_created} snapshot'
              f'{"s" if total_created != 1 else ""} created from transaction history.',
              'success')

    return redirect(url_for('main.dashboard'))


# market_state is injected app-wide by inject_market_state() in __init__.py
