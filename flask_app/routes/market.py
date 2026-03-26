from flask import Blueprint, flash, redirect, url_for
from flask_login import login_required
from flask_app import db
from flask_app.models import Account, Stock
import yfinance as yf
import pytz
import pandas_market_calendars as mcal
from datetime import datetime

market_bp = Blueprint('market', __name__)

@market_bp.route('/refresh_market_data/<int:account_id>', methods=['GET'])
@login_required
def refresh_market_data(account_id):
    """Fetches and updates the latest stock prices for a user's account."""
    account = Account.query.get_or_404(account_id)
    stocks = Stock.query.filter_by(account_id=account_id).all()

    for stock in stocks:
        try:
            stock_data = yf.Ticker(stock.ticker).info
            if 'regularMarketPrice' in stock_data:
                stock.current_price = stock_data['regularMarketPrice']
        except Exception as e:
            flash(f"Failed to fetch market data for {stock.ticker}: {str(e)}", "error")

    db.session.commit()
    flash('Market pricing updated successfully.', 'success')
    return redirect(url_for('portfolio.view_positions', account_id=account_id))

# market_state is injected app-wide by inject_market_state() in routes.py — no duplicate needed here.