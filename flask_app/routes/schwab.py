"""
schwab.py
---------
Schwab Developer API integration.

Routes
------
  GET  /schwab/connect          — redirect user to Schwab OAuth page
  GET  /schwab/callback         — handle OAuth redirect, store tokens
  GET  /schwab/accounts         — JSON: list linked Schwab accounts (for link modal)
  POST /schwab/link/<acct_id>   — save schwab_account_hash onto a WealthWise account
  POST /schwab/sync/<acct_id>   — sync positions + transactions from Schwab into account
  POST /schwab/disconnect       — delete stored tokens for current user

Token lifecycle
---------------
  Access token  : 30 min  — refreshed automatically before any API call
  Refresh token : 7 days  — requires re-auth via /schwab/connect after expiry
"""

import os
import base64
import requests as http
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, redirect, url_for, request,
                   flash, jsonify, render_template, session)
from flask_login import login_required, current_user

from flask_app import db
from flask_app.models import Account, Holding, Transaction, SchwabToken

schwab_bp = Blueprint('schwab', __name__, url_prefix='/schwab')

# ── Config ────────────────────────────────────────────────────────────────────

APP_KEY      = os.getenv('SCHWAB_APP_KEY')
APP_SECRET   = os.getenv('SCHWAB_APP_SECRET')
CALLBACK_URL = os.getenv('SCHWAB_CALLBACK_URL',
                         'https://www.wealthtrackapp.com/schwab/callback')

AUTH_URL    = 'https://api.schwabapi.com/v1/oauth/authorize'
TOKEN_URL   = 'https://api.schwabapi.com/v1/oauth/token'
API_BASE    = 'https://api.schwabapi.com/trader/v1'

# ── Helpers ───────────────────────────────────────────────────────────────────

def _basic_auth_header():
    """Base64-encoded Basic auth header for token endpoint."""
    creds = base64.b64encode(f"{APP_KEY}:{APP_SECRET}".encode()).decode()
    return {'Authorization': f'Basic {creds}',
            'Content-Type': 'application/x-www-form-urlencoded'}


def _bearer_header(token: SchwabToken):
    return {'Authorization': f'Bearer {token.access_token}'}


def _ensure_fresh_token(token: SchwabToken) -> bool:
    """
    Refresh access token if it's expired (or close to expiring).
    Returns True on success, False if refresh failed.
    """
    if not token.is_access_token_expired():
        return True

    resp = http.post(TOKEN_URL, headers=_basic_auth_header(), data={
        'grant_type':    'refresh_token',
        'refresh_token': token.refresh_token,
    }, timeout=10)

    if not resp.ok:
        return False

    data = resp.json()
    token.access_token        = data['access_token']
    token.access_token_issued = datetime.utcnow()
    if 'refresh_token' in data:
        token.refresh_token        = data['refresh_token']
        token.refresh_token_issued = datetime.utcnow()
    db.session.commit()
    return True


def _get_token_or_redirect():
    """
    Return the SchwabToken for the current user, or None if not connected /
    refresh token has expired (caller should handle redirect to /schwab/connect).
    """
    token = SchwabToken.query.filter_by(user_id=current_user.id).first()
    if token is None:
        return None
    if token.is_refresh_token_expired():
        return None
    return token


# ── OAuth routes ──────────────────────────────────────────────────────────────

@schwab_bp.route('/connect')
@login_required
def connect():
    """Redirect user to Schwab's OAuth authorization page."""
    if not APP_KEY or not APP_SECRET:
        flash('Schwab API credentials are not configured.', 'danger')
        return redirect(url_for('admin.manage_user', user_id=current_user.id))

    # Stash the user ID in the session BEFORE leaving the site.
    # This survives the cross-site redirect back from Schwab even when the
    # browser doesn't send the login cookie on the return trip (SameSite rules).
    session['schwab_connect_user_id'] = current_user.id
    session.modified = True

    auth_url = (
        f"{AUTH_URL}"
        f"?client_id={APP_KEY}"
        f"&redirect_uri={CALLBACK_URL}"
    )
    return redirect(auth_url)


@schwab_bp.route('/callback')
def callback():
    """
    Handle Schwab OAuth callback — no @login_required here.

    Schwab appends:  ?code=<auth_code>&session=<session_id>
    The code is URL-encoded and ends with %40 (i.e. '@').
    Flask's request.args decodes it, so request.args['code'] already ends with '@'.

    We identify the user via the session key written in /connect, falling back to
    flask-login's current_user if the session cookie happened to survive intact.
    """
    # Resolve the user — prefer the stashed ID, fall back to active login
    user_id = session.pop('schwab_connect_user_id', None)
    if user_id is None:
        if current_user.is_authenticated:
            user_id = current_user.id
        else:
            flash('Session expired — please log in and try connecting Schwab again.', 'warning')
            return redirect(url_for('auth.login'))

    error = request.args.get('error')
    if error:
        flash(f'Schwab authorization failed: {error}', 'danger')
        return redirect(url_for('admin.manage_user', user_id=user_id))

    code = request.args.get('code')
    if not code:
        flash('No authorization code received from Schwab.', 'danger')
        return redirect(url_for('admin.manage_user', user_id=user_id))

    # Exchange code for tokens
    resp = http.post(TOKEN_URL, headers=_basic_auth_header(), data={
        'grant_type':   'authorization_code',
        'code':         code,
        'redirect_uri': CALLBACK_URL,
    }, timeout=10)

    if not resp.ok:
        flash(f'Token exchange failed ({resp.status_code}). Please try again.', 'danger')
        return redirect(url_for('admin.manage_user', user_id=user_id))

    data = resp.json()
    now  = datetime.utcnow()

    # Upsert — one token row per user
    token = SchwabToken.query.filter_by(user_id=user_id).first()
    if token is None:
        token = SchwabToken(
            user_id              = user_id,
            access_token         = data['access_token'],
            refresh_token        = data['refresh_token'],
            id_token             = data.get('id_token'),
            access_token_issued  = now,
            refresh_token_issued = now,
        )
        db.session.add(token)
    else:
        token.access_token         = data['access_token']
        token.refresh_token        = data['refresh_token']
        token.id_token             = data.get('id_token')
        token.access_token_issued  = now
        token.refresh_token_issued = now

    db.session.commit()
    flash('Schwab account connected successfully!', 'success')
    return redirect(url_for('admin.manage_user', user_id=user_id))


@schwab_bp.route('/disconnect', methods=['POST'])
@login_required
def disconnect():
    """Remove stored Schwab tokens and unlink all accounts."""
    token = SchwabToken.query.filter_by(user_id=current_user.id).first()
    if token:
        db.session.delete(token)

    # Clear all schwab_account_hash values for this user's accounts
    Account.query.filter_by(user_id=current_user.id).update(
        {'schwab_account_hash': None}, synchronize_session=False
    )
    db.session.commit()
    flash('Schwab account disconnected.', 'success')
    return redirect(url_for('admin.manage_user', user_id=current_user.id))


# ── Account linking ───────────────────────────────────────────────────────────

@schwab_bp.route('/accounts')
@login_required
def list_schwab_accounts():
    """
    JSON endpoint: returns the list of Schwab accounts linked to this user's
    OAuth token. Used by the link-account modal.

    Returns:
    {
      "accounts": [{"accountNumber": "...", "hashValue": "..."}, ...],
      "linked_hashes": ["hash1", ...]   # hashes already linked to a WealthWise account
    }
    """
    token = _get_token_or_redirect()
    if token is None:
        return jsonify({'error': 'not_connected'}), 401

    if not _ensure_fresh_token(token):
        return jsonify({'error': 'token_refresh_failed'}), 401

    resp = http.get(f'{API_BASE}/accounts/accountNumbers',
                    headers=_bearer_header(token), timeout=10)
    if not resp.ok:
        return jsonify({'error': f'schwab_api_error_{resp.status_code}'}), 502

    # [{"accountNumber": "...", "hashValue": "..."}, ...]
    accounts = resp.json()

    # Hashes already linked to one of this user's WealthWise accounts
    linked_hashes = [
        a.schwab_account_hash
        for a in Account.query.filter_by(user_id=current_user.id).all()
        if a.schwab_account_hash
    ]

    return jsonify({'accounts': accounts, 'linked_hashes': linked_hashes})


@schwab_bp.route('/link/<int:account_id>', methods=['POST'])
@login_required
def link_account(account_id):
    """Save the Schwab account hash onto a WealthWise account."""
    account = Account.query.filter_by(
        id=account_id, user_id=current_user.id).first_or_404()

    schwab_hash = request.form.get('schwab_account_hash', '').strip()
    if not schwab_hash:
        flash('No Schwab account selected.', 'warning')
        return redirect(url_for('accounts.view_account', account_id=account_id))

    account.schwab_account_hash = schwab_hash
    db.session.commit()
    flash(f'"{account.account_name}" is now linked to a Schwab account.', 'success')
    return redirect(url_for('accounts.view_account', account_id=account_id))


@schwab_bp.route('/unlink/<int:account_id>', methods=['POST'])
@login_required
def unlink_account(account_id):
    """Remove the Schwab account hash from a WealthWise account."""
    account = Account.query.filter_by(
        id=account_id, user_id=current_user.id).first_or_404()
    account.schwab_account_hash = None
    db.session.commit()
    flash(f'"{account.account_name}" unlinked from Schwab.', 'success')
    return redirect(url_for('accounts.view_account', account_id=account_id))


# ── Sync ──────────────────────────────────────────────────────────────────────

@schwab_bp.route('/sync/<int:account_id>', methods=['POST'])
@login_required
def sync_account(account_id):
    """
    Pull live positions and recent transactions from Schwab and sync them
    into the WealthWise account.

    Positions  → upserts Holding rows  (quantity + cost_basis)
    Transactions → inserts new Transaction rows (deduped by date+action+ticker+amount)
    """
    account = Account.query.filter_by(
        id=account_id, user_id=current_user.id).first_or_404()

    if not account.schwab_account_hash:
        flash('This account is not linked to a Schwab account yet.', 'warning')
        return redirect(url_for('accounts.view_account', account_id=account_id))

    token = _get_token_or_redirect()
    if token is None:
        flash('Schwab is not connected. Please reconnect in Settings.', 'warning')
        return redirect(url_for('admin.manage_user', user_id=current_user.id))

    if not _ensure_fresh_token(token):
        flash('Could not refresh Schwab token. Please reconnect.', 'danger')
        return redirect(url_for('admin.manage_user', user_id=current_user.id))

    acct_hash = account.schwab_account_hash
    synced_positions    = 0
    synced_transactions = 0
    errors              = []

    # ── Positions ──────────────────────────────────────────────────────────
    pos_resp = http.get(
        f'{API_BASE}/accounts/{acct_hash}',
        headers=_bearer_header(token),
        params={'fields': 'positions'},
        timeout=15,
    )

    if pos_resp.ok:
        pos_data  = pos_resp.json()
        positions = pos_data.get('securitiesAccount', {}).get('positions', [])

        for pos in positions:
            instrument = pos.get('instrument', {})
            ticker     = instrument.get('symbol', '').strip().upper()
            if not ticker:
                continue

            qty        = float(pos.get('longQuantity', 0))
            avg_price  = float(pos.get('averagePrice', 0))
            cost_basis = round(qty * avg_price, 4) if qty and avg_price else None

            # Upsert holding
            holding = Holding.query.filter_by(
                account_id=account_id, ticker=ticker).first()

            if holding:
                holding.quantity     = qty
                holding.cost_basis   = cost_basis
                holding.last_updated = datetime.utcnow()
            else:
                holding = Holding(
                    ticker       = ticker,
                    quantity     = qty,
                    account_id   = account_id,
                    cost_basis   = cost_basis,
                    last_updated = datetime.utcnow(),
                )
                db.session.add(holding)

            synced_positions += 1

    else:
        errors.append(f'Positions API error ({pos_resp.status_code})')

    # ── Transactions ────────────────────────────────────────────────────────
    end_date   = datetime.utcnow()
    start_date = end_date - timedelta(days=90)  # last 90 days

    txn_resp = http.get(
        f'{API_BASE}/accounts/{acct_hash}/transactions',
        headers=_bearer_header(token),
        params={
            'startDate': start_date.strftime('%Y-%m-%dT00:00:00.000Z'),
            'endDate':   end_date.strftime('%Y-%m-%dT23:59:59.000Z'),
            'types':     'TRADE,DIVIDEND_OR_INTEREST,ACH_RECEIPT,ACH_DISBURSEMENT,'
                         'CASH_RECEIPT,CASH_DISBURSEMENT,ELECTRONIC_FUND,WIRE_OUT,WIRE_IN',
        },
        timeout=15,
    )

    if txn_resp.ok:
        raw_txns = txn_resp.json() if txn_resp.text else []

        # Build a set of existing transaction fingerprints to avoid duplicates
        existing = {
            (t.date, t.action_type, t.ticker, t.amount)
            for t in Transaction.query.filter_by(account_id=account_id).all()
        }

        for raw in raw_txns:
            txn_type    = raw.get('type', '')
            action_type = _map_schwab_txn_type(txn_type)
            txn_date_str = raw.get('tradeDate') or raw.get('settleDate') or ''
            txn_date     = _parse_iso_date(txn_date_str)
            if txn_date is None:
                continue

            # Instrument may be nested differently in API vs CSV
            instrument  = raw.get('transferItems', [{}])[0].get('instrument', {}) \
                          if raw.get('transferItems') else {}
            ticker      = instrument.get('symbol', '').strip().upper() or None
            quantity    = abs(float(raw.get('transferItems', [{}])[0].get('amount', 0) or 0)) \
                          if raw.get('transferItems') else None
            price       = abs(float(raw.get('transferItems', [{}])[0].get('price', 0) or 0)) \
                          if raw.get('transferItems') else None
            net_amount  = float(raw.get('netAmount', 0) or 0)
            description = raw.get('description', '').strip() or None

            fingerprint = (txn_date, action_type, ticker, round(net_amount, 4))
            if fingerprint in existing:
                continue

            txn = Transaction(
                account_id    = account_id,
                date          = txn_date,
                action_type   = action_type,
                raw_action    = txn_type,
                ticker        = ticker,
                description   = description,
                quantity      = quantity,
                price         = price,
                fees          = None,
                amount        = net_amount,
                import_source = 'schwab_api',
            )
            db.session.add(txn)
            existing.add(fingerprint)
            synced_transactions += 1

    else:
        errors.append(f'Transactions API error ({txn_resp.status_code})')

    db.session.commit()

    if errors:
        flash(f'Sync completed with errors: {"; ".join(errors)}', 'warning')
    else:
        parts = []
        if synced_positions:
            parts.append(f'{synced_positions} position{"s" if synced_positions != 1 else ""}')
        if synced_transactions:
            parts.append(f'{synced_transactions} new transaction{"s" if synced_transactions != 1 else ""}')
        summary = ' and '.join(parts) if parts else 'no new data'
        flash(f'Schwab sync complete — {summary} updated.', 'success')

    return redirect(url_for('portfolio.view_positions', account_id=account_id))


# ── Type mapping helpers ──────────────────────────────────────────────────────

_SCHWAB_API_TYPE_MAP = {
    'TRADE':                'buy',      # refined below by net_amount sign
    'DIVIDEND_OR_INTEREST': 'dividend',
    'ACH_RECEIPT':          'transfer_in',
    'ACH_DISBURSEMENT':     'transfer_out',
    'CASH_RECEIPT':         'transfer_in',
    'CASH_DISBURSEMENT':    'transfer_out',
    'ELECTRONIC_FUND':      'transfer_in',
    'WIRE_IN':              'transfer_in',
    'WIRE_OUT':             'transfer_out',
    'JOURNAL':              'other',
    'MEMORANDUM':           'other',
    'MARGIN_CALL':          'fee',
    'MONEY_MARKET':         'other',
    'SMA_ADJUSTMENT':       'other',
    'RECEIVE_AND_DELIVER':  'other',
}


def _map_schwab_txn_type(raw_type: str) -> str:
    return _SCHWAB_API_TYPE_MAP.get(raw_type.upper(), 'other')


def _parse_iso_date(date_str: str):
    """Parse ISO 8601 date string to datetime.date, return None on failure."""
    if not date_str:
        return None
    # Strip time portion if present
    date_part = date_str[:10]
    try:
        return datetime.strptime(date_part, '%Y-%m-%d').date()
    except ValueError:
        return None
