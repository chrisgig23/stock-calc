from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask_app.models import Account, PortfolioSnapshot, Holding, Transaction, ACTION_SELL, ACTION_DIVIDEND, ACTION_BUY
from flask_app.utils.price_cache import get_price
from sqlalchemy import func
import json

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/view_reports/<int:account_id>', methods=['GET'])
@login_required
def view_reports(account_id):
    """Portfolio performance reports: growth chart, per-ticker table, transaction summary."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    # ── Growth chart data ─────────────────────────────────────────────────
    snapshots = (PortfolioSnapshot.query
                 .filter_by(account_id=account_id)
                 .order_by(PortfolioSnapshot.snapshot_date.asc())
                 .all())

    chart_labels = [s.snapshot_date.strftime('%b %-d, %Y') for s in snapshots]
    chart_market = [round(s.total_market_value, 2) for s in snapshots]
    chart_cost   = [round(s.total_cost_basis, 2) if s.total_cost_basis else None
                    for s in snapshots]

    # ── Current holdings performance table ───────────────────────────────
    current_holdings = Holding.query.filter_by(account_id=account_id).order_by(Holding.ticker).all()

    holdings_perf = []
    for h in current_holdings:
        price     = h.current_price
        mv        = round(h.quantity * price, 2)
        cb        = h.cost_basis
        cb_share  = round(cb / h.quantity, 4) if cb and h.quantity > 0 else None
        gain      = round(mv - cb, 2) if cb is not None else None
        gain_pct  = round((mv - cb) / cb * 100, 2) if cb and cb > 0 else None
        holdings_perf.append({
            'ticker':     h.ticker,
            'quantity':   h.quantity,
            'price':      round(price, 2),
            'mv':         mv,
            'cost_basis': round(cb, 2) if cb is not None else None,
            'cb_share':   cb_share,
            'gain':       gain,
            'gain_pct':   gain_pct,
            'included':   h.isincluded,
        })

    # Sort server-side so the template doesn't have to handle None comparisons
    holdings_perf.sort(key=lambda h: h['gain_pct'] if h['gain_pct'] is not None else 0, reverse=True)

    # Compute abs_max for the gain bar width calculation
    gain_pcts = [h['gain_pct'] for h in holdings_perf if h['gain_pct'] is not None]
    abs_max   = max((abs(g) for g in gain_pcts), default=1) or 1

    # ── Overall summary stats ─────────────────────────────────────────────
    current_value = round(sum(h['mv'] for h in holdings_perf), 2)
    current_cost  = round(sum(h['cost_basis'] for h in holdings_perf
                              if h['cost_basis'] is not None), 2)
    total_gain     = round(current_value - current_cost, 2) if current_cost else None
    total_gain_pct = round(total_gain / current_cost * 100, 2) if current_cost else None
    start_value    = snapshots[0].total_market_value if snapshots else None

    # ── Transaction summary ───────────────────────────────────────────────
    all_txns = Transaction.query.filter_by(account_id=account_id).all()

    total_invested  = round(abs(sum(t.amount for t in all_txns
                                    if t.action_type == ACTION_BUY)), 2)
    total_dividends = round(sum(t.amount for t in all_txns
                                if t.action_type in ('dividend', 'reinvest_dividend')), 2)
    total_fees      = round(sum(t.fees or 0 for t in all_txns), 2)
    total_interest  = round(sum(t.amount for t in all_txns
                                if t.action_type == 'interest'), 2)

    # Realized gain from sells
    sell_txns     = [t for t in all_txns if t.action_type == ACTION_SELL]
    realized_gain = None
    if sell_txns:
        total_proceeds = sum(t.amount for t in sell_txns)
        # We don't store cost basis at time of sell, so we approximate from current CB ratio
        # For now, show proceeds total
        realized_gain = round(total_proceeds, 2)

    txn_summary = {
        'total_transactions': len(all_txns),
        'buy_count':          sum(1 for t in all_txns if t.action_type == ACTION_BUY),
        'sell_count':         len(sell_txns),
        'total_invested':     total_invested,
        'total_dividends':    total_dividends,
        'total_interest':     total_interest,
        'total_fees':         total_fees,
        'sell_proceeds':      realized_gain,
    }

    # ── SPY benchmark for chart ───────────────────────────────────────────
    # Fetch current SPY price and build a simple benchmark overlay if we have snapshots
    spy_chart_values = []
    if snapshots:
        spy_price_now = get_price('SPY')
        if spy_price_now and spy_price_now > 0 and start_value:
            # Approximate SPY performance as a multiplier from start date
            # We don't have historical SPY prices in our DB, so we annotate the
            # start/end growth ratio as a reference text rather than a full series.
            spy_gain_approx = None  # placeholder — would need historical data for full line

    return render_template(
        'reports.html',
        account=account,
        snapshots=snapshots,
        chart_labels=json.dumps(chart_labels),
        chart_market=json.dumps(chart_market),
        chart_cost=json.dumps(chart_cost),
        current_value=current_value,
        current_cost=current_cost,
        total_gain=total_gain,
        total_gain_pct=total_gain_pct,
        start_value=start_value,
        holdings_perf=holdings_perf,
        abs_max=abs_max,
        txn_summary=txn_summary,
    )
