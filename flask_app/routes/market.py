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

@market_bp.context_processor
def inject_market_state():
    """Determines if the stock market is currently open or closed."""
    today = datetime.now().strftime('%Y-%m-%d')
    schedule = mcal.get_calendar("NYSE").schedule(start_date=today, end_date=today)

    if not schedule.empty:
        market_open = schedule.iloc[0]["market_open"].tz_convert('America/New_York')
        market_close = schedule.iloc[0]["market_close"].tz_convert('America/New_York')
        current_time = datetime.now(pytz.timezone('America/New_York'))
        market_state = market_open <= current_time <= market_close
    else:
        market_state = False

    return dict(market_state=market_state)