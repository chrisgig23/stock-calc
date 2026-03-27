from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account, Holding
from datetime import datetime

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

# market_state is injected app-wide by inject_market_state() in __init__.py
