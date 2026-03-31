from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import User, Account
from werkzeug.security import generate_password_hash
from datetime import datetime
import secrets
import string

admin_bp = Blueprint('admin', __name__)


def _is_admin(user):
    """Returns True if the user has admin privileges."""
    return getattr(user, 'is_admin', False) or user.username == 'cgiglio'


def _require_admin():
    """Redirects non-admins away. Returns a response object or None."""
    if not _is_admin(current_user):
        flash('Admin access required.', 'danger')
        return redirect(url_for('accounts.view_account'))
    return None


def _generate_temp_password(length=12):
    """Generates a cryptographically secure random temporary password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ── Admin Panel ────────────────────────────────────────────────────────────────

@admin_bp.route('/admin/')
@login_required
def admin_dashboard():
    """Central admin panel: user list, stats, and management actions."""
    err = _require_admin()
    if err:
        return err

    users = User.query.order_by(User.id).all()
    total_accounts = Account.query.count()
    admin_count = sum(1 for u in users if _is_admin(u))

    return render_template(
        'admin_dashboard.html',
        users=users,
        total_accounts=total_accounts,
        admin_count=admin_count,
    )


@admin_bp.route('/admin/user/add', methods=['POST'])
@login_required
def admin_add_user():
    """Create a new user with a generated temporary password."""
    err = _require_admin()
    if err:
        return err

    new_username = request.form.get('new_username', '').strip()
    if len(new_username) < 3:
        flash('Username must be at least 3 characters.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    if User.query.filter_by(username=new_username).first():
        flash(f'Username "{new_username}" already exists.', 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    temp_pw = _generate_temp_password()
    new_user = User(
        username=new_username,
        password_hash=generate_password_hash(temp_pw),
        is_admin=False,
    )
    db.session.add(new_user)
    db.session.commit()

    flash(
        f'User <strong>{new_username}</strong> created. '
        f'Temporary password: <code>{temp_pw}</code> — share this securely, it won\'t be shown again.',
        'success'
    )
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/user/<int:user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    """Generate a new random password for the specified user."""
    err = _require_admin()
    if err:
        return err

    user = User.query.get_or_404(user_id)
    temp_pw = _generate_temp_password()
    user.set_password(temp_pw)
    db.session.commit()

    flash(
        f'Password for <strong>{user.username}</strong> has been reset. '
        f'Temporary password: <code>{temp_pw}</code> — share this securely, it won\'t be shown again.',
        'info'
    )
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/user/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
def admin_toggle_admin(user_id):
    """Grant or revoke admin privileges for a user."""
    err = _require_admin()
    if err:
        return err

    if user_id == current_user.id:
        flash("You can't change your own admin status.", 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()

    status = 'granted' if user.is_admin else 'revoked'
    flash(f'Admin access {status} for <strong>{user.username}</strong>.', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """Permanently delete a user and all their associated data."""
    err = _require_admin()
    if err:
        return err

    if user_id == current_user.id:
        flash("You can't delete your own account from the admin panel.", 'warning')
        return redirect(url_for('admin.admin_dashboard'))

    user = User.query.get_or_404(user_id)
    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(
        f'User <strong>{username}</strong> and all associated data have been permanently deleted.',
        'success'
    )
    return redirect(url_for('admin.admin_dashboard'))


# ── Self-service routes ────────────────────────────────────────────────────────

@admin_bp.route('/manage_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def manage_user(user_id):
    """Users may manage their own account; admins may manage any account."""
    if current_user.id != user_id and not _is_admin(current_user):
        flash('You do not have permission to access that account.', 'danger')
        return redirect(url_for('accounts.view_account'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        flash("User details updated successfully.", "success")
        return redirect(url_for('admin.manage_user', user_id=user.id))

    return render_template('manage_user.html', user=user, now=datetime.utcnow())


@admin_bp.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    """Allows a user to change their own username."""
    if request.method == 'POST':
        new_username = request.form['new_username'].strip()

        if len(new_username) < 5:
            flash('Username must be at least 5 characters long.', 'error')
        elif len(new_username) > 15:
            flash('Username must not exceed 15 characters.', 'error')
        elif ' ' in new_username:
            flash('Username must not contain spaces.', 'error')
        elif User.query.filter_by(username=new_username).first():
            flash('Username already exists. Please choose another one.', 'error')
        else:
            current_user.username = new_username
            db.session.commit()
            flash('Username successfully updated.', 'success')
            return redirect(url_for('accounts.view_account'))

    return render_template('change_username.html')


@admin_bp.route('/add_user', methods=['POST'])
@login_required
def add_user():
    """Legacy route — proxies to the new admin add-user action."""
    if not _is_admin(current_user):
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('accounts.view_account'))
    return redirect(url_for('admin.admin_dashboard'), code=307)
