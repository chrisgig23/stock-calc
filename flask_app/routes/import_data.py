"""
import_data.py
-------------
Handles CSV imports from brokerage exports (currently Schwab).

Routes
------
GET  /import/<account_id>                  — import landing page
POST /import/positions/<account_id>        — Schwab positions CSV → holdings
POST /import/transactions/<account_id>     — Schwab transactions CSV → transactions
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account, Holding, Transaction
from flask_app.utils.schwab_parser import parse_schwab_positions, parse_schwab_transactions
from datetime import datetime

import_bp = Blueprint('import_data', __name__)


def _account_or_403(account_id):
    """Return the account if it belongs to the current user, else 403."""
    account = Account.query.get_or_404(account_id)
    if account.user_id != current_user.id:
        from flask import abort
        abort(403)
    return account


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@import_bp.route('/import/<int:account_id>', methods=['GET'])
@login_required
def import_page(account_id):
    account = _account_or_403(account_id)
    return render_template('import.html', account=account)


# ---------------------------------------------------------------------------
# Positions import  (Step 1 — seed current holdings + cost basis)
# ---------------------------------------------------------------------------

@import_bp.route('/import/positions/<int:account_id>', methods=['POST'])
@login_required
def import_positions(account_id):
    account = _account_or_403(account_id)
    file = request.files.get('file')

    if not file or file.filename == '':
        flash('Please select a file before importing.', 'error')
        return redirect(url_for('import_data.import_page', account_id=account_id))

    try:
        content = file.read().decode('utf-8-sig')   # utf-8-sig strips BOM if present
    except Exception:
        flash('Could not read the file. Make sure it is saved as UTF-8.', 'error')
        return redirect(url_for('import_data.import_page', account_id=account_id))

    parsed = parse_schwab_positions(content)

    if not parsed:
        flash(
            'No positions found in that file. '
            'Make sure you exported from Accounts → Positions → Export in Schwab.',
            'error'
        )
        return redirect(url_for('import_data.import_page', account_id=account_id))

    imported = 0
    updated  = 0
    now      = datetime.utcnow()

    for item in parsed:
        existing = Holding.query.filter_by(
            account_id=account_id, ticker=item['ticker']
        ).first()

        if existing:
            existing.quantity     = item['quantity']
            existing.cost_basis   = item['cost_basis']
            existing.last_updated = now
            updated += 1
        else:
            holding = Holding(
                ticker       = item['ticker'],
                quantity     = item['quantity'],
                account_id   = account_id,
                cost_basis   = item['cost_basis'],
                isincluded   = True,
                last_updated = now,
            )
            db.session.add(holding)
            imported += 1

    db.session.commit()

    flash(
        f'Positions import complete — {imported} new holding(s) added, '
        f'{updated} existing holding(s) updated.',
        'success'
    )
    return redirect(url_for('portfolio.view_positions', account_id=account_id))


# ---------------------------------------------------------------------------
# Transactions import  (Step 2 — load transaction history)
# ---------------------------------------------------------------------------

@import_bp.route('/import/transactions/<int:account_id>', methods=['POST'])
@login_required
def import_transactions(account_id):
    account = _account_or_403(account_id)
    file = request.files.get('file')

    if not file or file.filename == '':
        flash('Please select a file before importing.', 'error')
        return redirect(url_for('import_data.import_page', account_id=account_id))

    try:
        content = file.read().decode('utf-8-sig')
    except Exception:
        flash('Could not read the file. Make sure it is saved as UTF-8.', 'error')
        return redirect(url_for('import_data.import_page', account_id=account_id))

    parsed = parse_schwab_transactions(content)

    if not parsed:
        flash(
            'No transactions found in that file. '
            'Make sure you exported from Accounts → History → Export in Schwab.',
            'error'
        )
        return redirect(url_for('import_data.import_page', account_id=account_id))

    imported = 0
    skipped  = 0

    for item in parsed:
        # Deduplicate: same account + date + action + ticker + amount
        dupe = Transaction.query.filter_by(
            account_id  = account_id,
            date        = item['date'],
            action_type = item['action_type'],
            ticker      = item['ticker'],
            amount      = item['amount'],
        ).first()

        if dupe:
            skipped += 1
            continue

        txn = Transaction(account_id=account_id, **item)
        db.session.add(txn)
        imported += 1

    db.session.commit()

    flash(
        f'Transaction import complete — {imported} new transaction(s) added, '
        f'{skipped} duplicate(s) skipped.',
        'success'
    )
    return redirect(url_for('import_data.import_page', account_id=account_id))
