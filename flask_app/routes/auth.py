from flask import Blueprint, render_template, render_template_string, redirect, url_for, request, flash, session, jsonify, current_app
from flask_login import login_user, login_required, logout_user, current_user
from flask_app import db, limiter
from flask_app.models import User
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
import pytz
import secrets
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
# Invite-action token helpers (approve / deny from email)
# ---------------------------------------------------------------------------

def _make_invite_action_token(name: str, email: str, specific_code: str = None) -> str:
    """Create a signed, time-limited token encoding the requester's name, email, and optional code."""
    serializer = _get_reset_serializer()
    payload = {'name': name, 'email': email}
    if specific_code:
        payload['code'] = specific_code
    return serializer.dumps(payload, salt='invite-action')


def _load_invite_action_data(token: str, max_age: int = 604800):
    """Return {'name': ..., 'email': ...} for a valid token, else None. Default: 7 days."""
    serializer = _get_reset_serializer()
    try:
        return serializer.loads(token, salt='invite-action', max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


# Simple inline HTML template for invite action result pages (no login required)
_INVITE_RESULT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{ title }} — WealthTrack</title>
  <style>
    body { margin:0; padding:0; background:#0f172a; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
           display:flex; align-items:center; justify-content:center; min-height:100vh; }
    .card { background:#1e293b; border-radius:14px; padding:40px 48px; max-width:420px; text-align:center;
            box-shadow:0 4px 24px rgba(0,0,0,0.4); }
    .icon { font-size:3rem; margin-bottom:16px; }
    h1 { color:#f8fafc; font-size:1.4rem; margin:0 0 12px; }
    p { color:#94a3b8; line-height:1.6; margin:0 0 28px; }
    a.btn { display:inline-block; background:#6d28d9; color:#fff; text-decoration:none;
            padding:11px 24px; border-radius:8px; font-weight:600; font-size:0.9rem; }
    a.btn:hover { background:#5b21b6; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">{{ "✅" if success else "⚠️" }}</div>
    <h1>{{ title }}</h1>
    <p>{{ message }}</p>
    <a href="{{ dashboard_url }}" class="btn">Go to WealthTrack</a>
  </div>
</body>
</html>
"""


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


# ---------------------------------------------------------------------------
# Sign up — invite-code-gated self-service account creation
# ---------------------------------------------------------------------------

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("5 per hour", methods=['POST'])
def signup():
    """Public sign-up page. Requires a valid invite code."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username        = request.form.get('username', '').strip()
        email           = request.form.get('email', '').strip().lower()
        invite_code     = request.form.get('invite_code', '').strip()
        password        = request.form.get('password', '')
        confirm         = request.form.get('confirm_password', '')

        # ── Validate invite code ──────────────────────────────────────────
        from flask_app.models import SiteConfig, InviteCode
        import os
        # Primary: check InviteCode table (supports multiple active codes)
        # Fallback: legacy SiteConfig / env var for backward compatibility
        code_valid = InviteCode.is_valid(invite_code)
        if not code_valid:
            legacy = SiteConfig.get('invite_code') or os.getenv('INVITE_CODE', '')
            code_valid = bool(legacy) and secrets.compare_digest(invite_code, legacy)
        if not code_valid:
            flash('Invalid invite code. Please check your code and try again.', 'danger')
            return render_template('signup.html', username=username, email=email)

        # ── Validate fields ───────────────────────────────────────────────
        if not username or len(username) < 3:
            flash('Username must be at least 3 characters.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if not email or '@' not in email:
            flash('Please enter a valid email address.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('signup.html', username=username, email=email)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html', username=username, email=email)

        # ── Check uniqueness ──────────────────────────────────────────────
        if User.query.filter_by(username=username).first():
            flash('That username is already taken.', 'danger')
            return render_template('signup.html', email=email)

        if User.query.filter(
            User.email == email,
            User.email_verified == True  # noqa: E712
        ).first():
            flash('An account with that email already exists.', 'danger')
            return render_template('signup.html', username=username)

        # ── Create user ───────────────────────────────────────────────────
        from datetime import datetime as _dt
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            email_verified=False,
            must_change_password=False,
            invite_code_used=invite_code,
            created_at=_dt.utcnow(),
        )
        db.session.add(new_user)
        db.session.commit()
        InviteCode.record_use(invite_code)

        login_user(new_user)

        # Send email verification code
        code = new_user.generate_email_code()
        db.session.commit()
        from flask_app.email_utils import send_verification_email
        send_verification_email(email, code, username)

        flash(f'Welcome, {username}! Please verify your email to continue.', 'success')
        return redirect(url_for('auth.email_verify'))

    return render_template('signup.html', username='', email='')


@auth_bp.route('/signup/request-code', methods=['POST'])
@limiter.limit("3 per hour", methods=['POST'])
def request_invite_code():
    """Accept an invite code request and notify the admin — requester's info only."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    name  = request.form.get('requester_name', '').strip()
    email = request.form.get('requester_email', '').strip().lower()
    note  = request.form.get('requester_note', '').strip()

    if not name or not email or '@' not in email:
        flash('Please provide your name and a valid email address.', 'danger')
        return redirect(url_for('auth.signup'))

    # Build one approve URL per active invite code + a single deny URL
    from flask_app.models import InviteCode as _IC
    active_codes = _IC.query.order_by(_IC.created_at.desc()).all()

    deny_token = _make_invite_action_token(name, email)   # code-agnostic deny token
    deny_url   = url_for('auth.deny_invite', token=deny_token, _external=True)

    if active_codes:
        approve_options = []
        for ic in active_codes:
            tok = _make_invite_action_token(name, email, specific_code=ic.code)
            url = url_for('auth.approve_invite', token=tok, _external=True)
            approve_options.append((ic.code, url))
    else:
        # Fallback: legacy single-code token (may be empty)
        tok = _make_invite_action_token(name, email)
        approve_options = None
        legacy_approve_url = url_for('auth.approve_invite', token=tok, _external=True)

    from flask_app.email_utils import send_invite_request_notification
    if active_codes:
        send_invite_request_notification(name, email, note,
                                         deny_url=deny_url,
                                         approve_options=approve_options)
    else:
        send_invite_request_notification(name, email, note,
                                         approve_url=legacy_approve_url,
                                         deny_url=deny_url)

    flash("Request sent! If approved, you'll receive an invite code by email shortly.", 'success')
    return redirect(url_for('auth.signup'))


@auth_bp.route('/invite/approve/<token>')
def approve_invite(token):
    """One-click invite approval link sent to the admin in the notification email."""
    data = _load_invite_action_data(token)
    if not data:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Link Expired",
            message="This approval link has expired or is invalid. You can still send the invite code manually.",
            success=False,
            dashboard_url=url_for('main.dashboard'),
        ), 400

    name  = data['name']
    email = data['email']

    from flask_app.models import SiteConfig, InviteCode as _IC
    import os as _os
    # Use the code baked into the token (if admin clicked a specific-code button);
    # otherwise fall back to most recent active code or legacy SiteConfig/env
    invite_code = (data.get('code') or
                   getattr(_IC.query.order_by(_IC.created_at.desc()).first(), 'code', None) or
                   SiteConfig.get('invite_code') or
                   _os.getenv('INVITE_CODE', ''))
    if not invite_code:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="No Invite Code Set",
            message="There is no invite code configured in the admin panel. Please set one and send it manually.",
            success=False,
            dashboard_url=url_for('main.dashboard'),
        ), 400

    from flask_app.email_utils import send_invite_approval_email
    sent = send_invite_approval_email(email, name, invite_code)

    if sent:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Invite Sent!",
            message=f"The invite code was sent to {email}. They can now sign up at wealthtrackapp.com.",
            success=True,
            dashboard_url=url_for('main.dashboard'),
        )
    else:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Email Failed",
            message=f"Couldn't deliver the invite code to {email}. Check your Resend configuration and send it manually.",
            success=False,
            dashboard_url=url_for('main.dashboard'),
        ), 500


@auth_bp.route('/invite/deny/<token>')
def deny_invite(token):
    """One-click invite denial link sent to the admin in the notification email."""
    data = _load_invite_action_data(token)
    if not data:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Link Expired",
            message="This denial link has expired or is invalid.",
            success=False,
            dashboard_url=url_for('main.dashboard'),
        ), 400

    name  = data['name']
    email = data['email']

    from flask_app.email_utils import send_invite_denial_email
    sent = send_invite_denial_email(email, name)

    if sent:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Denial Sent",
            message=f"A cordial decline was sent to {email}.",
            success=True,
            dashboard_url=url_for('main.dashboard'),
        )
    else:
        return render_template_string(
            _INVITE_RESULT_HTML,
            title="Email Failed",
            message=f"Couldn't send the denial to {email}. Check your Resend configuration.",
            success=False,
            dashboard_url=url_for('main.dashboard'),
        ), 500


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
