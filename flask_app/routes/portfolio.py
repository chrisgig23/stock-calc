from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account, Holding, Transaction, Allocation, ACTION_BUY
from datetime import datetime
import yfinance as yf

portfolio_bp = Blueprint('portfolio', __name__)


# ---------------------------------------------------------------------------
# View Positions
# ---------------------------------------------------------------------------

@portfolio_bp.route('/view_positions/<int:account_id>', methods=['GET'])
@login_required
def view_positions(account_id):
    """Displays all current holdings with live prices and cost basis."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    holdings = Holding.query.filter_by(account_id=account_id).all()

    # Most recent transaction date for context
    last_txn = (Transaction.query
                .filter_by(account_id=account_id)
                .order_by(Transaction.date.desc())
                .first())
    last_txn_date = last_txn.date if last_txn else None

    total_market_value  = sum(h.market_value for h in holdings)
    total_cost_basis    = sum(h.cost_basis for h in holdings if h.cost_basis is not None)
    total_unrealized    = round(total_market_value - total_cost_basis, 2) if total_cost_basis else None
    included_mv         = sum(h.market_value for h in holdings if h.isincluded)
    tracked_mv          = sum(h.market_value for h in holdings if not h.isincluded)

    return render_template(
        'view_positions.html',
        account=account,
        holdings=holdings,
        last_txn_date=last_txn_date,
        total_market_value=total_market_value,
        total_cost_basis=total_cost_basis,
        total_unrealized=total_unrealized,
        included_market_value=included_mv,
        tracked_market_value=tracked_mv,
    )


# ---------------------------------------------------------------------------
# Edit Portfolio  (manual holding management)
# ---------------------------------------------------------------------------

@portfolio_bp.route('/edit_portfolio/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio(account_id):
    """Allows users to manually add, update, or remove holdings."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        tickers     = request.form.getlist('tickers[]')
        quantities  = request.form.getlist('quantities[]')
        cost_bases  = request.form.getlist('cost_bases[]')
        new_tickers     = request.form.getlist('new_tickers[]')
        new_quantities  = request.form.getlist('new_quantities[]')
        new_cost_bases  = request.form.getlist('new_cost_bases[]')
        now = datetime.utcnow()

        # Process existing holdings
        for i, ticker in enumerate(tickers):
            if request.form.get(f'delete_{ticker}'):
                Holding.query.filter_by(account_id=account_id, ticker=ticker).delete()
                continue

            quantity   = float(quantities[i]) if quantities[i] else 0
            isincluded = request.form.get(f'isincluded_{ticker}', 'off') == 'on'
            cb_raw     = cost_bases[i].replace('$', '').replace(',', '').strip() if i < len(cost_bases) and cost_bases[i] else None
            cost_basis = float(cb_raw) if cb_raw else None

            holding = Holding.query.filter_by(account_id=account_id, ticker=ticker).first()
            if holding:
                holding.quantity      = quantity
                holding.isincluded    = isincluded
                holding.cost_basis    = cost_basis
                holding.last_updated  = now

        # Process new holdings
        for i, ticker in enumerate(new_tickers):
            ticker = ticker.strip().upper()
            if not ticker:
                continue

            # Validate ticker via yfinance
            try:
                info = yf.Ticker(ticker).info
            except Exception:
                info = {}
            if 'shortName' not in info and 'longName' not in info:
                flash(f"Ticker '{ticker}' not found — please verify and try again.", 'error')
                holdings = Holding.query.filter_by(account_id=account_id).all()
                return render_template('edit_portfolio.html', account=account, holdings=holdings)

            qty    = float(new_quantities[i]) if i < len(new_quantities) and new_quantities[i] else 0
            cb_raw = new_cost_bases[i].replace('$', '').replace(',', '').strip() if i < len(new_cost_bases) and new_cost_bases[i] else None
            cb     = float(cb_raw) if cb_raw else None

            existing = Holding.query.filter_by(account_id=account_id, ticker=ticker).first()
            if existing:
                existing.quantity     = qty
                existing.cost_basis   = cb
                existing.last_updated = now
            else:
                db.session.add(Holding(
                    ticker=ticker, quantity=qty, account_id=account_id,
                    cost_basis=cb, isincluded=True, last_updated=now
                ))

        db.session.commit()
        flash('Portfolio updated successfully!', 'success')
        return redirect(url_for('accounts.view_account', account_id=account.id))

    holdings = Holding.query.filter_by(account_id=account_id).all()
    return render_template('edit_portfolio.html', account=account, holdings=holdings)


# ---------------------------------------------------------------------------
# Allocation views
# ---------------------------------------------------------------------------

@portfolio_bp.route('/view_allocation/<int:account_id>')
@login_required
def view_allocation(account_id):
    """Displays current vs. target allocation for included holdings."""
    account  = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    included = Holding.query.filter_by(account_id=account.id, isincluded=True).all()
    total_mv = sum(h.market_value for h in included)
    allocations = []

    for h in included:
        current_pct = (h.market_value / total_mv * 100) if total_mv > 0 else 0
        target      = Allocation.query.filter_by(account_id=account.id, name=h.ticker).first()
        allocations.append({
            'ticker':              h.ticker,
            'current_allocation':  round(current_pct, 2),
            'target_allocation':   round(target.target, 2) if target else 0,
        })

    return render_template('view_allocation.html', account=account, allocations=allocations)


@portfolio_bp.route('/adjust_allocation/<int:account_id>', methods=['GET', 'POST'])
@login_required
def adjust_allocation(account_id):
    """Allows users to set target allocations per ticker."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        names   = request.form.getlist('allocation_name')
        targets = request.form.getlist('allocation_target')

        for name, target in zip(names, targets):
            alloc = Allocation.query.filter_by(account_id=account.id, name=name).first()
            if alloc:
                alloc.target = float(target)
            else:
                db.session.add(Allocation(name=name, target=float(target), account_id=account.id))

        db.session.commit()
        flash('Allocations updated successfully!', 'success')
        return redirect(url_for('portfolio.view_allocation', account_id=account.id))

    holdings = Holding.query.filter_by(account_id=account.id).all()
    allocations = []
    total_mv = sum(h.market_value for h in holdings if h.isincluded)
    for h in holdings:
        target_row  = Allocation.query.filter_by(account_id=account.id, name=h.ticker).first()
        current_pct = round(h.market_value / total_mv * 100, 2) if (total_mv > 0 and h.isincluded) else 0
        allocations.append({
            'name':       h.ticker,
            'target':     round(target_row.target, 2) if target_row else 0,
            'isincluded': h.isincluded,
            'current':    current_pct,
        })

    return render_template('adjust_allocation.html', account=account, allocations=allocations)


# ---------------------------------------------------------------------------
# Make a Purchase  (allocation-based buy suggestions)
# ---------------------------------------------------------------------------

@portfolio_bp.route('/make_purchase/<int:account_id>', methods=['GET', 'POST'])
@login_required
def make_purchase(account_id):
    """Suggests purchases based on target allocation and available cash."""
    account  = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    included = Holding.query.filter_by(account_id=account_id, isincluded=True).all()

    # Ensure allocations sum to 100 for included tickers
    included_tickers = {h.ticker for h in included}
    total_target = (db.session.query(db.func.sum(Allocation.target))
                    .filter(Allocation.account_id == account_id,
                            Allocation.name.in_(included_tickers))
                    .scalar() or 0)

    if abs(total_target - 100) > 0.01:
        flash("Please set desired allocation (must total 100%) before making a purchase.", 'warning')
        return redirect(url_for('portfolio.adjust_allocation', account_id=account_id))

    last_txn = (Transaction.query
                .filter_by(account_id=account_id, action_type=ACTION_BUY)
                .order_by(Transaction.date.desc())
                .first())
    last_purchase_date = last_txn.date if last_txn else None

    if request.method == 'POST':
        if 'submit_purchase' in request.form:
            now = datetime.utcnow()
            for key, value in request.form.items():
                if not key.startswith('quantity_'):
                    continue
                qty = int(value) if value else 0
                if qty <= 0:
                    continue

                ticker  = key.split('_', 1)[1]
                holding = Holding.query.filter_by(account_id=account_id, ticker=ticker).first()
                if not holding:
                    holding = Holding(
                        ticker=ticker, quantity=0, account_id=account_id,
                        isincluded=True, last_updated=now
                    )
                    db.session.add(holding)
                    db.session.flush()

                price = holding.current_price
                cost  = round(price * qty, 2)

                # Update holding
                holding.quantity     += qty
                holding.cost_basis    = (holding.cost_basis or 0) + cost
                holding.last_updated  = now

                # Record buy transaction
                db.session.add(Transaction(
                    account_id   = account_id,
                    date         = now.date(),
                    action_type  = ACTION_BUY,
                    raw_action   = 'Buy',
                    ticker       = ticker,
                    quantity     = qty,
                    price        = price,
                    fees         = None,
                    amount       = -cost,
                    import_source = 'manual',
                ))

            db.session.commit()
            flash("Purchase recorded successfully!", 'success')
            return redirect(url_for('portfolio.view_positions', account_id=account.id))

        elif 'cash_value' in request.form:
            cash_value = float(request.form['cash_value'])
            suggested  = _get_suggested_purchases(account, included, cash_value)
            return render_template(
                'make_purchase.html',
                account=account,
                suggested_purchases=suggested,
                cash_value=cash_value,
                last_purchase_date=last_purchase_date,
            )

    return render_template('make_purchase.html', account=account, last_purchase_date=last_purchase_date)


def _get_suggested_purchases(account, included_holdings, cash_value):
    """Calculates suggested share purchases to close allocation gaps."""
    allocations = Allocation.query.filter_by(account_id=account.id).all()
    alloc_dict  = {a.name: a.target for a in allocations}
    total_mv    = sum(h.market_value for h in included_holdings)
    suggestions = []
    total_cost  = 0.0

    gaps = []
    for h in included_holdings:
        current_pct = (h.market_value / total_mv * 100) if total_mv > 0 else 0
        target_pct  = alloc_dict.get(h.ticker, 0)
        gaps.append((h, target_pct - current_pct))
    gaps.sort(key=lambda x: x[1], reverse=True)

    for h, gap in gaps:
        price = h.current_price
        if price > 0 and gap > 0:
            target_value = alloc_dict.get(h.ticker, 0) / 100 * (total_mv + cash_value)
            target_qty   = int(target_value / price)
            max_qty      = int((cash_value - total_cost) / price)
            qty          = min(target_qty - int(h.quantity), max_qty)
            cost         = round(qty * price, 2)
            if qty > 0 and total_cost + cost <= cash_value:
                suggestions.append({
                    'name':                h.ticker,
                    'current_price':       price,
                    'current_position':    h.quantity,
                    'suggested_quantity':  qty,
                    'estimated_total_cost': cost,
                })
                total_cost += cost

    return suggestions


# ---------------------------------------------------------------------------
# Ticker validation endpoint
# ---------------------------------------------------------------------------

@portfolio_bp.route('/validate_tickers', methods=['POST'])
@login_required
def validate_tickers():
    data    = request.get_json()
    tickers = data.get('tickers', [])
    valid, invalid = [], []

    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
        except Exception:
            info = {}
        if 'shortName' in info or 'longName' in info:
            valid.append(f"{ticker} - {info.get('shortName') or info.get('longName', 'Unknown')}")
        else:
            invalid.append(ticker)

    if invalid:
        return jsonify(valid=False, invalid_tickers=invalid)
    return jsonify(valid=True, matches=valid)
