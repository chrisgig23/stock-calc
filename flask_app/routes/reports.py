from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask_app.models import Account, PortfolioSnapshot, Holding
import json

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/view_reports/<int:account_id>', methods=['GET'])
@login_required
def view_reports(account_id):
    """Portfolio performance reports: growth chart + summary stats."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    # Pull snapshots in chronological order
    snapshots = (PortfolioSnapshot.query
                 .filter_by(account_id=account_id)
                 .order_by(PortfolioSnapshot.snapshot_date.asc())
                 .all())

    # Build chart data series
    chart_labels      = [s.snapshot_date.strftime('%b %Y') for s in snapshots]
    chart_market      = [round(s.total_market_value, 2) for s in snapshots]
    chart_cost        = [round(s.total_cost_basis, 2) if s.total_cost_basis else None
                         for s in snapshots]

    # Summary stats
    current_holdings = Holding.query.filter_by(account_id=account_id).all()
    current_value    = round(sum(h.market_value for h in current_holdings), 2)
    current_cost     = round(sum(h.cost_basis for h in current_holdings
                                 if h.cost_basis is not None), 2)
    total_gain       = round(current_value - current_cost, 2) if current_cost else None
    total_gain_pct   = round(total_gain / current_cost * 100, 2) if current_cost else None

    start_value = snapshots[0].total_market_value if snapshots else None

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
    )