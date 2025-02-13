from flask import Blueprint, redirect, url_for
from flask_login import current_user

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def root():
    """Redirects unauthenticated users to the login page without flashing an unauthorized message."""
    if current_user.is_authenticated:
        return redirect(url_for('accounts.view_account'))  # Redirect to the account page
    return redirect(url_for('auth.login'))  # Show login page, but without a "not authorized" message