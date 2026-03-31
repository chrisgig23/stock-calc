from flask_app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import yfinance as yf
from datetime import datetime
from flask_app.utils.encryption import EncryptedText
import secrets


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id                       = db.Column(db.Integer, primary_key=True)
    username                 = db.Column(db.String(150), unique=True, nullable=False)
    password_hash            = db.Column(db.String(256), nullable=False)
    is_admin                 = db.Column(db.Boolean, nullable=False, default=False)
    must_change_password     = db.Column(db.Boolean, nullable=False, default=False)

    # ── Email (migration away from username login) ──────────────────────
    email                    = db.Column(db.String(255), unique=True, nullable=True)
    email_verified           = db.Column(db.Boolean, nullable=False, default=False)
    email_verification_code  = db.Column(db.String(6), nullable=True)   # 6-digit OTP
    email_code_expires       = db.Column(db.DateTime, nullable=True)

    accounts = db.relationship('Account', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_accounts(self):
        return Account.query.filter_by(user_id=self.id).order_by(Account.position.asc()).all()

    def generate_email_code(self):
        """Generate a fresh 6-digit verification code, valid for 15 minutes."""
        from datetime import timedelta
        self.email_verification_code = f"{secrets.randbelow(1_000_000):06d}"
        self.email_code_expires = datetime.utcnow() + timedelta(minutes=15)
        return self.email_verification_code

    def verify_email_code(self, code: str) -> bool:
        """Return True if the code matches and hasn't expired."""
        if not self.email_verification_code or not self.email_code_expires:
            return False
        if datetime.utcnow() > self.email_code_expires:
            return False
        return secrets.compare_digest(self.email_verification_code, code.strip())

    def clear_email_code(self):
        self.email_verification_code = None
        self.email_code_expires = None


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

class Account(db.Model):
    __tablename__ = 'accounts'

    id           = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(50), nullable=False)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    position             = db.Column(db.Integer, nullable=False, default=0)
    brokerage            = db.Column(db.String(50), nullable=True)   # e.g. "Schwab", "Fidelity"
    schwab_account_hash  = db.Column(db.String(128), nullable=True)  # encrypted hash for Schwab API

    holdings    = db.relationship('Holding',           backref='account', lazy=True, cascade='all, delete-orphan')
    allocations = db.relationship('Allocation',        backref='account', lazy=True, cascade='all, delete-orphan')
    transactions= db.relationship('Transaction',       backref='account', lazy=True, cascade='all, delete-orphan')
    snapshots   = db.relationship('PortfolioSnapshot', backref='account', lazy=True, cascade='all, delete-orphan')

    def get_holdings(self):
        return Holding.query.filter_by(account_id=self.id).all()

    def get_allocations(self):
        return Allocation.query.filter_by(account_id=self.id).all()

    def __repr__(self):
        return f'<Account {self.account_name} (user {self.user_id})>'


# ---------------------------------------------------------------------------
# Holding  (replaces Stock)
# Current share positions — seeded by Schwab import, editable manually.
# ---------------------------------------------------------------------------

class Holding(db.Model):
    __tablename__ = 'holdings'

    id           = db.Column(db.Integer, primary_key=True)
    account_id   = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    ticker       = db.Column(db.String(10), nullable=False)
    quantity     = db.Column(db.Float, nullable=False, default=0)
    cost_basis   = db.Column(db.Float, nullable=True)   # total cost basis (all lots)
    isincluded   = db.Column(db.Boolean, nullable=False, default=True)
    last_updated = db.Column(db.DateTime, nullable=True)

    def __init__(self, ticker, quantity, account_id, cost_basis=None, isincluded=True, last_updated=None):
        self.ticker       = ticker.upper()
        self.quantity     = quantity
        self.account_id   = account_id
        self.cost_basis   = cost_basis
        self.isincluded   = isincluded
        self.last_updated = last_updated

    # ---- live price (yfinance) ----

    @property
    def current_price(self):
        try:
            info = yf.Ticker(self.ticker).info
            return (info.get('currentPrice')
                    or info.get('regularMarketPreviousClose')
                    or info.get('navPrice')
                    or info.get('open')
                    or 0.0)
        except Exception:
            return 0.0

    # ---- derived properties ----

    @property
    def market_value(self):
        return round(self.quantity * self.current_price, 2)

    @property
    def cost_basis_per_share(self):
        if self.cost_basis and self.quantity and self.quantity > 0:
            return round(self.cost_basis / self.quantity, 4)
        return None

    @property
    def unrealized_gain(self):
        if self.cost_basis is not None:
            return round(self.market_value - self.cost_basis, 2)
        return None

    @property
    def unrealized_gain_pct(self):
        if self.cost_basis and self.cost_basis > 0:
            return round((self.market_value - self.cost_basis) / self.cost_basis * 100, 2)
        return None

    def __repr__(self):
        return f'<Holding {self.ticker} x{self.quantity} in account {self.account_id}>'


# ---------------------------------------------------------------------------
# Allocation  (unchanged)
# ---------------------------------------------------------------------------

class Allocation(db.Model):
    __tablename__ = 'allocations'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(64), nullable=False)   # ticker symbol
    target     = db.Column(db.Float, nullable=False)         # target %
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)

    def __repr__(self):
        return f'<Allocation {self.name} → {self.target}% in account {self.account_id}>'


# ---------------------------------------------------------------------------
# Transaction  (replaces Purchase)
# Every financial event: buy, sell, dividend, transfer, interest, fee, …
# ---------------------------------------------------------------------------

# Canonical action_type values
ACTION_BUY               = 'buy'
ACTION_SELL              = 'sell'
ACTION_DIVIDEND          = 'dividend'
ACTION_REINVEST_DIVIDEND = 'reinvest_dividend'
ACTION_REINVEST_SHARES   = 'reinvest_shares'
ACTION_TRANSFER_IN       = 'transfer_in'
ACTION_TRANSFER_OUT      = 'transfer_out'
ACTION_INTEREST          = 'interest'
ACTION_FEE               = 'fee'
ACTION_OTHER             = 'other'

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id          = db.Column(db.Integer, primary_key=True)
    account_id  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    date        = db.Column(db.Date, nullable=False)
    action_type = db.Column(db.String(25), nullable=False)   # see ACTION_* constants above
    ticker      = db.Column(db.String(20), nullable=True)    # null for cash-only events
    description = db.Column(db.String(200), nullable=True)
    quantity    = db.Column(db.Float, nullable=True)         # shares
    price       = db.Column(db.Float, nullable=True)         # per-share price
    fees        = db.Column(db.Float, nullable=True)
    amount      = db.Column(db.Float, nullable=False)        # net cash: + = credit, - = debit
    import_source = db.Column(db.String(50), nullable=True)  # e.g. 'schwab_transactions_csv'
    raw_action    = db.Column(db.String(50), nullable=True)  # original string from brokerage

    def __repr__(self):
        return (f'<Transaction {self.date} {self.action_type} '
                f'{self.ticker or "CASH"} ${self.amount}>')


# ---------------------------------------------------------------------------
# PortfolioSnapshot  (new)
# One row per account per day — powers the growth chart.
# Written by the /snapshot route or a scheduled task.
# ---------------------------------------------------------------------------

class PortfolioSnapshot(db.Model):
    __tablename__ = 'portfolio_snapshots'

    id                 = db.Column(db.Integer, primary_key=True)
    account_id         = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    snapshot_date      = db.Column(db.Date, nullable=False)
    total_market_value = db.Column(db.Float, nullable=False)
    total_cost_basis   = db.Column(db.Float, nullable=True)
    cash_balance       = db.Column(db.Float, nullable=True, default=0.0)
    dividend_income    = db.Column(db.Float, nullable=True, default=0.0)  # cumulative YTD
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('account_id', 'snapshot_date', name='uq_snapshot_account_date'),
    )

    def __repr__(self):
        return f'<PortfolioSnapshot {self.snapshot_date} account {self.account_id} ${self.total_market_value}>'


# ---------------------------------------------------------------------------
# SchwabToken  — OAuth tokens for Schwab API, one row per user
# ---------------------------------------------------------------------------

class SchwabToken(db.Model):
    __tablename__ = 'schwab_tokens'

    id                   = db.Column(db.Integer, primary_key=True)
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    access_token         = db.Column(EncryptedText, nullable=False)
    refresh_token        = db.Column(EncryptedText, nullable=False)
    id_token             = db.Column(EncryptedText, nullable=True)
    access_token_issued  = db.Column(db.DateTime, nullable=False)
    refresh_token_issued = db.Column(db.DateTime, nullable=False)

    user = db.relationship('User', backref=db.backref('schwab_token', uselist=False))

    def is_access_token_expired(self):
        """Access tokens last 30 minutes."""
        return (datetime.utcnow() - self.access_token_issued).total_seconds() > 1740  # 29 min

    def is_refresh_token_expired(self):
        """Refresh tokens last 7 days."""
        return (datetime.utcnow() - self.refresh_token_issued).days >= 7

    def __repr__(self):
        return f'<SchwabToken user={self.user_id} issued={self.access_token_issued}>'
