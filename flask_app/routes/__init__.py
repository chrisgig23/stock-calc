from .auth import auth_bp
from .accounts import accounts_bp
from .portfolio import portfolio_bp
from .market import market_bp
from .reports import reports_bp
from .main import main_bp
from .admin import admin_bp

def register_routes(app):
    """Registers all route Blueprints to the Flask app."""
    app.register_blueprint(auth_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
