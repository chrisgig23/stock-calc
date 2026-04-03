from flask import Blueprint, render_template, redirect, url_for, request, flash, session, jsonify, current_app
from flask_login import login_user, login_required, logout_user, current_user
from flask_app import db, limiter
from flask_app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

auth_bp = Blueprint('auth', __name__)


def _get_reset_serializer():
    secret_key = current_app.config['SECRET_KEY']
    if isinstance(secret_key, bytes):
        secret_key = secret_key.decode('utf-8', 'replace')
    return URLSafeTimedSerializer(secret_key)


def _make_password_reset_token(user):
    """Create a time-limited reset token invalidated by future password changes."""
    serializer = _get_reset_serializer()
    return serializer.dumps(
        {'uid': user.id, 'pwd': user.password_hash[-16:]},
        salt='password-reset',
    )


def _load_password_reset_user(token, max_age=3600):
    """Return the matching user for a valid reset token, else None."""
    serializer = _get_reset_serializer()
    try:
        data = serializer.loads(token, salt='password-reset', max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None

    user = User.query.get(data.get('uid'))
    if not user:
        return None

    if data.get('pwd') != user.password_hash[-16:]:
        return None

    return user

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


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes", methods=['POST'])
def forgot_password():
    """Start a self-service password reset via verified email."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if email and '@' in email:
            user = User.query.filter(
                User.email == email,
                User.email_verified == True  # noqa: E712
            ).first()
            if user:
                token = _make_password_reset_token(user)
                reset_url = url_for('auth.reset_password_token', token=token, _external=True)

                from flask_app.email_utils import send_password_reset_email
                send_password_reset_email(user.email, user.username, reset_url)

        flash(
            "If we found a verified account with that email address, we've sent a password reset link.",
            'info'
        )
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')

# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@auth_bp.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
@login_required
def reset_password(user_id):
    user = User.query.get(user_id)
    if not user:
        flash('User does not exist.', 'danger')
        return redirect(url_for('auth.login'))

    if current_user.id != user.id:
        flash('Use the admin reset flow to reset another user password.', 'warning')
        return redirect(url_for('admin.manage_user', user_id=user.id))

    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if len(new_password) < 8:
            flash('Please choose a password with at least 8 characters.', 'danger')
        elif new_password == confirm_password:
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = False
            db.session.commit()
            logout_user()
            flash('Password updated successfully. Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Passwords do not match.', 'danger')

    return render_template(
        'reset_password.html',
        user=user,
        cancel_url=url_for('admin.manage_user', user_id=user.id),
        reset_context='signed_in',
    )


@auth_bp.route('/reset-password/token/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    """Reset a password using an emailed time-limited link."""
    user = _load_password_reset_user(token)
    if not user:
        flash('That reset link is invalid or has expired. Please request a new one.', 'warning')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not new_password or len(new_password) < 8:
            flash('Please choose a password with at least 8 characters.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = False
            db.session.commit()

            if current_user.is_authenticated:
                logout_user()
            session.clear()
            flash('Password updated successfully. Please sign in with your new password.', 'success')
            return redirect(url_for('auth.login'))

    return render_template(
        'reset_password.html',
        user=user,
        cancel_url=url_for('auth.login'),
        reset_context='email_link',
    )

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
