from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()  # Load environment variables

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY').encode('utf-8', 'replace')
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
from flask_app.models import User, Account, Stock, Purchase

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

# Import and register Blueprints
from flask_app.routes.auth import auth_bp
from flask_app.routes.accounts import accounts_bp
from flask_app.routes.portfolio import portfolio_bp
from flask_app.routes.market import market_bp
from flask_app.routes.reports import reports_bp
from flask_app.routes.main import main_bp
from flask_app.routes.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(accounts_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(market_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(main_bp)
app.register_blueprint(admin_bp)