from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
import pytz
import pandas_market_calendars as mcal
from datetime import datetime, timedelta

load_dotenv()  # Load environment variables

class Config:
    _flask_env = os.getenv('FLASK_ENV', 'production')
    SQLALCHEMY_DATABASE_URI = (
        'sqlite:////tmp/stock_calc_dev.db'
        if _flask_env == 'development'
        else os.getenv('DATABASE_URL')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = (os.getenv('SECRET_KEY') or 'dev-key-for-local-testing').encode('utf-8', 'replace')
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

# Initialize the app and apply the configuration
app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'  # Redirects to login if not authenticated

# Import models
from flask_app.models import User, Account, Holding

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Ensure user_id is an integer

@app.context_processor
def inject_accounts():
    """Ensures 'accounts' and 'max_position' are accessible in all templates globally."""
    if current_user.is_authenticated:
        user_accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.position).all()
        max_position = db.session.query(db.func.max(Account.position)).filter_by(user_id=current_user.id).scalar() or 0
        return {"accounts": user_accounts, "max_position": max_position}
    return {"accounts": [], "max_position": 0}

@app.context_processor
def inject_market_state():
    """Injects market open/closed state into all templates.
    Uses NYSE calendar; falls back to a simple weekday+time check if the
    calendar library has no data for today."""
    try:
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        today = now_ny.strftime('%Y-%m-%d')
        schedule = mcal.get_calendar('NYSE').schedule(start_date=today, end_date=today)

        if not schedule.empty:
            market_open  = schedule.iloc[0]['market_open'].tz_convert('America/New_York')
            market_close = schedule.iloc[0]['market_close'].tz_convert('America/New_York')
            market_state = market_open <= now_ny <= market_close
        else:
            # Fallback: Mon–Fri, 9:30 AM – 4:00 PM ET (no holiday awareness)
            from datetime import time as dt_time
            market_state = (
                now_ny.weekday() < 5 and
                dt_time(9, 30) <= now_ny.time() <= dt_time(16, 0)
            )
    except Exception:
        market_state = False

    return dict(market_state=market_state)

# Import and register Blueprints
from flask_app.routes.auth import auth_bp
from flask_app.routes.accounts import accounts_bp
from flask_app.routes.portfolio import portfolio_bp
from flask_app.routes.market import market_bp
from flask_app.routes.reports import reports_bp
from flask_app.routes.main import main_bp
from flask_app.routes.admin import admin_bp
from flask_app.routes.import_data import import_bp
from flask_app.routes.schwab import schwab_bp

app.register_blueprint(auth_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(market_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(import_bp)
app.register_blueprint(schwab_bp)