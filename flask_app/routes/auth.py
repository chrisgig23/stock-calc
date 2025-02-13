from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from flask_app import db
from flask_app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz

auth_bp = Blueprint('auth', __name__)

@auth_bp.before_request
def make_session_permanent():
    """Ensures user session remains active unless expired."""
    session.permanent = True

@auth_bp.before_request
def session_management():
    """Manages session expiration and auto-logout."""
    now = datetime.now(pytz.utc)
    last_activity = session.get('last_activity', now)

    if isinstance(last_activity, str):
        last_activity = datetime.fromisoformat(last_activity)

    session['last_activity'] = now
    if (now - last_activity).total_seconds() > 3600:  # Example: 1-hour timeout
        session.clear()
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

@auth_bp.route('/extend-session', methods=['POST'])
@login_required
def extend_session():
    """Extends the user's session to prevent auto-logout."""
    session['last_activity'] = datetime.now(pytz.utc).isoformat()
    return jsonify(success=True)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login and authentication."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if check_password_hash(user.password_hash, 'password1'):
                return redirect(url_for('auth.reset_password', user_id=user.id))
            else:
                login_user(user)
                return redirect(url_for('accounts.view_account'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    """Logs the user out and clears session data."""
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    """Allows users to reset their password."""
    user = User.query.get(user_id)
    if not user:
        flash('User does not exist.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            logout_user()
            flash('Password reset successfully. Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Passwords do not match.', 'danger')
    
    return render_template('reset_password.html', user=user)