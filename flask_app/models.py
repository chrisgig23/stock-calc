from flask_app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import yfinance as yf

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Relationship with Account
    accounts = db.relationship('Account', backref='owner', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_accounts(self):
        return self.accounts

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships with Stock, Position, and Allocation
    stocks = db.relationship('Stock', backref='account', lazy=True)
    positions = db.relationship('Position', backref='account', lazy=True)
    allocations = db.relationship('Allocation', backref='account', lazy=True)
    
    def __repr__(self):
        return f'<Account {self.account_name} of User {self.user_id}>'

    def get_stocks(self):
        return self.stocks

    def get_positions(self):
        return self.positions

    def get_allocations(self):
        return self.allocations

class Stock(db.Model):
    __tablename__ = 'stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)

    def __init__(self, ticker, quantity, account_id):
        self.ticker = ticker.upper()  # Ensure ticker symbols are uppercase
        self.quantity = quantity
        self.account_id = account_id

    @property
    def current_price(self):
        stock_data = yf.Ticker(self.ticker).info
        
        # Use currentPrice if available, otherwise fall back to regularMarketPreviousClose, then navPrice, and finally open price.
        price = stock_data.get('currentPrice') or \
                stock_data.get('regularMarketPreviousClose') or \
                stock_data.get('navPrice') or \
                stock_data.get('open') or 0.0
                
        return price

    @property
    def market_value(self):
        return round(self.quantity * self.current_price, 2)

    def __repr__(self):
        return f'<Stock {self.ticker} in Account {self.account_id}>'

class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)

    def __repr__(self):
        return f'<Position {self.name} with quantity {self.quantity} in Account {self.account_id}>'

class Allocation(db.Model):
    __tablename__ = 'allocations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    target = db.Column(db.Float, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)

    def __repr__(self):
        return f'<Allocation {self.name} with target {self.target}% in Account {self.account_id}>'