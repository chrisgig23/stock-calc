from flask import Blueprint, redirect, url_for, render_template
from flask_login import current_user, login_required
from flask_app.models import Account, PortfolioSnapshot
from collections import defaultdict
from datetime import date
import yfinance as yf
import json

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def root():
    """Root redirect — authenticated users go to dashboard, others to login."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Portfolio Overview Dashboard — cross-account summary with charts."""
    accounts = current_user.get_accounts()

    if not accounts:
        return redirect(url_for('accounts.add_account'))

    # ── Gather all holdings across every account ──────────────────────────
    all_holdings = []
    for account in accounts:
        all_holdings.extend(account.holdings)

    # ── Fetch live prices once per unique ticker ───────────────────────────
    unique_tickers = list({h.ticker for h in all_holdings if h.ticker})
    prices = {}
    for ticker in unique_tickers:
        try:
            info = yf.Ticker(ticker).info
            prices[ticker] = (
                info.get('currentPrice')
                or info.get('regularMarketPreviousClose')
                or info.get('navPrice')
                or info.get('open')
                or 0.0
            )
        except Exception:
            prices[ticker] = 0.0

    # ── Aggregate by ticker across all accounts ────────────────────────────
    ticker_agg = {}
    for h in all_holdings:
        if h.ticker not in ticker_agg:
            ticker_agg[h.ticker] = {'market_value': 0.0, 'cost_basis': 0.0, 'quantity': 0.0}
        ticker_agg[h.ticker]['market_value'] += h.quantity * prices.get(h.ticker, 0.0)
        ticker_agg[h.ticker]['cost_basis']   += h.cost_basis or 0.0
        ticker_agg[h.ticker]['quantity']     += h.quantity

    # ── Chart 1 — Allocation pie (by ticker market value) ─────────────────
    pie_items = sorted(
        [(t, d['market_value']) for t, d in ticker_agg.items() if d['market_value'] > 0],
        key=lambda x: -x[1]
    )
    pie_labels = [t for t, _ in pie_items]
    pie_values = [round(v, 2) for _, v in pie_items]

    # ── Chart 2 — Portfolio Growth (PortfolioSnapshot) ─────────────────────
    account_ids = [a.id for a in accounts]
    snapshots = (
        PortfolioSnapshot.query
        .filter(PortfolioSnapshot.account_id.in_(account_ids))
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )

    growth_by_date = defaultdict(float)
    for snap in snapshots:
        growth_by_date[snap.snapshot_date.isoformat()] += snap.total_market_value

    # Always pin today's live value as the most recent data point
    today_str = date.today().isoformat()
    today_total = sum(d['market_value'] for d in ticker_agg.values())
    if today_total > 0:
        growth_by_date[today_str] = today_total

    growth_labels = sorted(growth_by_date.keys())
    growth_values  = [round(growth_by_date[d], 2) for d in growth_labels]
    has_growth_data = len(growth_labels) > 1  # need at least 2 points for a meaningful line

    # ── Chart 3 — Top Performers (% gain per ticker) ───────────────────────
    performers = []
    for ticker, data in ticker_agg.items():
        if data['cost_basis'] > 0 and data['market_value'] > 0:
            gain_pct = (data['market_value'] - data['cost_basis']) / data['cost_basis'] * 100
            performers.append({'ticker': ticker, 'gain_pct': round(gain_pct, 2)})
    performers.sort(key=lambda x: -x['gain_pct'])

    # ── Portfolio-level totals ─────────────────────────────────────────────
    total_market_value  = sum(d['market_value'] for d in ticker_agg.values())
    total_cost_basis_sum = sum(d['cost_basis']  for d in ticker_agg.values())
    has_cost_basis      = total_cost_basis_sum > 0
    total_cost_basis    = round(total_cost_basis_sum, 2) if has_cost_basis else None
    total_unrealized    = round(total_market_value - total_cost_basis_sum, 2) if has_cost_basis else None
    total_unrealized_pct = round(
        (total_unrealized / total_cost_basis_sum * 100), 2
    ) if (has_cost_basis and total_unrealized is not None) else None

    # ── Per-account summary cards (DASH2) ─────────────────────────────────
    account_cards = []
    for account in accounts:
        acct_mv = sum(h.quantity * prices.get(h.ticker, 0.0) for h in account.holdings)
        acct_cb = sum(h.cost_basis or 0.0 for h in account.holdings)
        acct_unreal     = round(acct_mv - acct_cb, 2) if acct_cb > 0 else None
        acct_unreal_pct = round(acct_unreal / acct_cb * 100, 2) if (acct_unreal is not None and acct_cb > 0) else None
        account_cards.append({
            'id':                 account.id,
            'name':               account.account_name,
            'total_market_value': round(acct_mv, 2),
            'total_cost_basis':   round(acct_cb, 2) if acct_cb > 0 else None,
            'unrealized':         acct_unreal,
            'unrealized_pct':     acct_unreal_pct,
        })

    return render_template(
        'dashboard.html',
        account_cards       = account_cards,
        pie_labels          = json.dumps(pie_labels),
        pie_values          = json.dumps(pie_values),
        performers          = json.dumps(performers),
        growth_labels       = json.dumps(growth_labels),
        growth_values       = json.dumps(growth_values),
        has_growth_data     = has_growth_data,
        has_holdings        = bool(all_holdings),
        total_market_value  = round(total_market_value, 2),
        total_cost_basis    = total_cost_basis,
        total_unrealized    = total_unrealized,
        total_unrealized_pct = total_unrealized_pct,
    )
