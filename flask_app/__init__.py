from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import os
import pytz
import pandas_market_calendars as mcal
from datetime import datetime, timedelta
import warnings

load_dotenv()  # Load environment variables

_flask_env = os.getenv('FLASK_ENV', 'production')
_is_prod   = _flask_env != 'development'

# Warn on startup if encryption key is missing
if not os.getenv('ENCRYPTION_KEY'):
    warnings.warn(
        "ENCRYPTION_KEY is not set — Schwab OAuth tokens will be stored unencrypted. "
        "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"",
        RuntimeWarning, stacklevel=1,
    )


class Config:
    # ── Database ────────────────────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = (
        'sqlite:////tmp/stock_calc_dev.db'
        if _flask_env == 'development'
        else os.getenv('DATABASE_URL')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Secret key ──────────────────────────────────────────────────────
    SECRET_KEY = (os.getenv('SECRET_KEY') or 'dev-key-for-local-testing-only').encode('utf-8', 'replace')

    # ── Session security ────────────────────────────────────────────────
    PERMANENT_SESSION_LIFETIME  = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY     = True                  # not accessible via JS
    SESSION_COOKIE_SAMESITE     = 'Lax'                 # CSRF mitigation
    SESSION_COOKIE_SECURE       = _is_prod              # HTTPS-only in production
    SESSION_COOKIE_NAME         = '__Host-session' if _is_prod else 'session'

    # ── Upload safety ───────────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload size

    # ── CSRF ────────────────────────────────────────────────────────────
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token validity

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

# ── CSRF protection (Flask-WTF) ──────────────────────────────────────────────
csrf = CSRFProtect(app)

# ── Rate limiter ─────────────────────────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],          # No global limit — apply per-route
    storage_uri='memory://',    # In-memory; swap for Redis in high-traffic prod
)

# ── Security response headers ────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers['X-Frame-Options']           = 'DENY'
    response.headers['X-Content-Type-Options']    = 'nosniff'
    response.headers['X-XSS-Protection']          = '1; mode=block'
    response.headers['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']        = 'geolocation=(), camera=(), microphone=()'
    if _is_prod:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Import models
from flask_app.models import User, Account, Holding

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Ensure user_id is an integer

@app.context_processor
def inject_schwab_status():
    """Exposes schwab_enabled to all templates. Flip SCHWAB_ENABLED=true in .env once
    the Schwab developer portal modification is approved."""
    return {"schwab_enabled": os.getenv("SCHWAB_ENABLED", "false").lower() == "true"}

@app.context_processor
def inject_accounts():
    """Ensures 'accounts' and 'max_position' are accessible in all templates globally."""
    if current_user.is_authenticated:
        user_accounts = Account.query.filter_by(user_id=current_user.id).order_by(Account.position).all()
        max_position = db.session.query(db.func.max(Account.position)).filter_by(user_id=current_user.id).scalar() or 0
        return {"accounts": user_accounts, "max_position": max_position}
    return {"accounts": [], "max_position": 0}

def _fmt_market_delta(delta, prefix):
    """Format a timedelta into a human-friendly string like 'Opens in 1h 30m'."""
    total = int(delta.total_seconds())
    if total <= 0:
        return ''
    h = total // 3600
    m = (total % 3600) // 60
    if h >= 48:
        return f'{prefix} in {h // 24}d'
    elif h > 0:
        return f'{prefix} in {h}h {m}m' if m else f'{prefix} in {h}h'
    else:
        return f'{prefix} in {m}m'


@app.context_processor
def inject_market_state():
    """Injects market_state (bool) and market_next_event (str) into all templates.
    Uses NYSE calendar with a 7-day lookahead to compute next open/close time."""
    try:
        ny_tz  = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        today  = now_ny.strftime('%Y-%m-%d')
        ahead  = (now_ny + timedelta(days=7)).strftime('%Y-%m-%d')

        schedule = mcal.get_calendar('NYSE').schedule(start_date=today, end_date=ahead)

        market_state      = False
        market_next_event = ''

        if not schedule.empty:
            for _, row in schedule.iterrows():
                open_et  = row['market_open'].tz_convert(ny_tz)
                close_et = row['market_close'].tz_convert(ny_tz)

                if open_et <= now_ny <= close_et:
                    market_state      = True
                    market_next_event = _fmt_market_delta(close_et - now_ny, 'Closes')
                    break
                elif now_ny < open_et:
                    market_next_event = _fmt_market_delta(open_et - now_ny, 'Opens')
                    break
                # Past session for this day — check next row
        else:
            # Fallback: Mon–Fri, 9:30 AM – 4:00 PM ET
            from datetime import time as dt_time
            market_state = (
                now_ny.weekday() < 5 and
                dt_time(9, 30) <= now_ny.time() <= dt_time(16, 0)
            )
    except Exception:
        market_state      = False
        market_next_event = ''

    return dict(market_state=market_state, market_next_event=market_next_event)

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