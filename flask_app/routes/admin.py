from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import User
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/manage_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def manage_user(user_id):
    """Allows an admin to manage a user's details."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        # Placeholder for handling form submission (e.g., updating user details)
        flash("User details updated successfully.", "success")
        return redirect(url_for('admin.manage_user', user_id=user.id))

    return render_template('manage_user.html', user=user)

@admin_bp.route('/change_username', methods=['GET', 'POST'])
@login_required
def change_username():
    """Allows a user to change their username."""
    if request.method == 'POST':
        new_username = request.form['new_username'].strip()

        # Validation checks
        if len(new_username) < 5:
            flash('Username must be at least 5 characters long.', 'error')
        elif len(new_username) > 15:
            flash('Username must not exceed 15 characters.', 'error')
        elif ' ' in new_username:
            flash('Username must not contain spaces.', 'error')
        elif User.query.filter_by(username=new_username).first():
            flash('Username already exists. Please choose another one.', 'error')
        else:
            # Update username
            current_user.username = new_username
            db.session.commit()
            flash('Username successfully updated.', 'success')
            return redirect(url_for('accounts.view_account'))

    return render_template('change_username.html')

@admin_bp.route('/add_user', methods=['POST'])
@login_required
def add_user():
    """Allows an admin to add a new user with a default password."""
    if current_user.username != 'cgiglio':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('accounts.view_account'))

    new_username = request.form.get('new_username')
    if new_username:
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user:
            flash('Username already exists.', 'warning')
        else:
            # Create the new user with the default password
            new_user = User(username=new_username, password_hash=generate_password_hash('password1'))
            db.session.add(new_user)
            db.session.commit()
            flash(f'User {new_username} added successfully with a temporary password "password1".', 'success')
    else:
        flash('Please enter a username.', 'warning')

    return redirect(url_for('accounts.view_account'))