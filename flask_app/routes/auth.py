from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import login_user, login_required, logout_user, current_user
from flask_app import db, limiter
from flask_app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz

auth_bp = Blueprint('auth', __name__)

# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@auth_bp.before_request
def make_session_permanent():
    session.permanent = True

@auth_bp.before_request
def session_management():
    now = datetime.now(pytz.utc)
    last_activity = session.get('last_activity', now)
    if isinstance(last_activity, str):
        last_activity = datetime.fromisoformat(last_activity)
    session['last_activity'] = now
    if (now - last_activity).total_seconds() > 3600:
        session.clear()
        flash('Your session has expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

@auth_bp.route('/extend-session', methods=['POST'])
@login_required
def extend_session():
    session['last_activity'] = datetime.now(pytz.utc).isoformat()
    return jsonify(success=True)

# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------

@auth_bp.route('/home', methods=['GET', 'POST'])
@limiter.limit("10 per minute", methods=['POST'])
def login():
    """Landing/home page with login form. Accepts username OR email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        login_id = request.form.get('login_id', '').strip()
        password = request.form.get('password', '')

        # Try username first, then email
        user = User.query.filter_by(username=login_id).first()
        if not user:
            user = User.query.filter(
                User.email == login_id,
                User.email_verified == True  # noqa: E712
            ).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)

            # Gate 1: forced password change (admin reset)
            if user.must_change_password:
                flash('Your password was reset by an admin. Please set a new password before continuing.', 'warning')
                return redirect(url_for('auth.reset_password', user_id=user.id))

            # Gate 2: email not yet verified — send them to capture flow
            if not user.email_verified:
                return redirect(url_for('auth.email_capture'))

            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')

    return render_template('home.html')


@auth_bp.route('/login')
def login_redirect():
    """Legacy /login URL — redirects to /home."""
    return redirect(url_for('auth.login'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('auth.login'))

# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@auth_bp.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User does not exist.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = False
            db.session.commit()
            logout_user()
            flash('Password updated successfully. Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template('reset_password.html', user=user)

# ---------------------------------------------------------------------------
# Email capture — ask the user for their email address
# ---------------------------------------------------------------------------

@auth_bp.route('/setup-email', methods=['GET', 'POST'])
@login_required
def email_capture():
    """
    Step 1 of email migration: collect the user's email address.
    Sends a 6-digit verification code, then redirects to the verify step.
    """
    # Already done — skip straight through
    if current_user.email_verified:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('email_capture.html')

        # Check it's not already taken by another verified user
        existing = User.query.filter(
            User.email == email,
            User.email_verified == True,  # noqa: E712
            User.id != current_user.id
        ).first()
        if existing:
            flash('That email address is already associated with another account.', 'danger')
            return render_template('email_capture.html')

        # Save email and generate OTP
        current_user.email = email
        code = current_user.generate_email_code()
        db.session.commit()

        # Send the code
        from flask_app.email_utils import send_verification_email
        sent = send_verification_email(email, code, current_user.username)

        if sent:
            flash(f'A 6-digit code was sent to {email}. It expires in 15 minutes.', 'info')
        else:
            flash('Email could not be sent. Please try again or contact support.', 'warning')

        return redirect(url_for('auth.email_verify'))

    return render_template('email_capture.html')


# ---------------------------------------------------------------------------
# Email verification — enter the 6-digit OTP
# ---------------------------------------------------------------------------

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
@login_required
def email_verify():
    """
    Step 2 of email migration: enter the verification code.
    """
    if current_user.email_verified:
        return redirect(url_for('main.dashboard'))

    if not current_user.email:
        return redirect(url_for('auth.email_capture'))

    # Mask email for display: jo**@example.com
    def _mask(addr):
        local, domain = addr.split('@', 1)
        visible = local[:2] if len(local) > 2 else local[0]
        return f"{visible}{'*' * max(1, len(local) - 2)}@{domain}"

    masked = _mask(current_user.email)

    if request.method == 'POST':
        # Accept either a single field "code" or six individual digit fields
        if 'code' in request.form:
            submitted = request.form['code'].strip()
        else:
            submitted = ''.join(
                request.form.get(f'd{i}', '').strip() for i in range(1, 7)
            )

        if current_user.verify_email_code(submitted):
            current_user.email_verified = True
            current_user.clear_email_code()
            db.session.commit()
            flash('Email verified! You can now log in with your email address going forward.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Incorrect or expired code. Please try again.', 'danger')

    return render_template('email_verify.html', masked_email=masked)


@auth_bp.route('/resend-code', methods=['POST'])
@login_required
@limiter.limit("3 per 10 minutes")
def resend_code():
    """Re-generate and resend the verification code."""
    if current_user.email_verified:
        return redirect(url_for('main.dashboard'))
    if not current_user.email:
        return redirect(url_for('auth.email_capture'))

    code = current_user.generate_email_code()
    db.session.commit()

    from flask_app.email_utils import send_verification_email
    sent = send_verification_email(current_user.email, code, current_user.username)

    if sent:
        flash('A new code has been sent to your email.', 'info')
    else:
        flash('Could not resend the code. Please try again shortly.', 'warning')

    return redirect(url_for('auth.email_verify'))
