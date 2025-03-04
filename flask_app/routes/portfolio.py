from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account, Stock, Purchase, Allocation
from datetime import datetime
import pytz
import yfinance as yf
from uuid import uuid4

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/make_purchase/<int:account_id>', methods=['GET', 'POST'])
@login_required
def make_purchase(account_id):
    """Handles purchasing stocks based on user allocation."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    # Debugging
    # allocations = db.session.query(Allocation.name, Allocation.target) \
    #     .filter(Allocation.account_id == account_id).all()

    # print("\nAllocations from Flask query:")
    # for allocation in allocations:
    #     print(f"Stock: {allocation.name}, Target: {allocation.target}")

    # included_stocks = db.session.query(Stock.ticker, Stock.isincluded) \
    #     .filter(Stock.account_id == account_id).all()

    # print("\nStocks and isIncluded status from Flask query:")
    # for stock in included_stocks:
    #     print(f"Stock: {stock.ticker}, isIncluded: {stock.isincluded}")

    total_target_allocation = db.session.query(db.func.sum(db.cast(Allocation.target, db.Float))) \
        .join(Stock, (Stock.ticker == Allocation.name) & (Stock.account_id == Allocation.account_id)) \
        .filter(Stock.account_id == account_id, Stock.isincluded == True) \
        .scalar() or 0

    # Debugging
    # print(f"\nComputed Total Target Allocation: {total_target_allocation}")
    if total_target_allocation != 100:
        flash("Please set desired allocation before making a purchase.", 'warning')
        return redirect(url_for('portfolio.adjust_allocation', account_id=account_id))

    last_purchase = Purchase.query.join(Stock, Purchase.stock_id == Stock.id) \
                                  .filter(Stock.account_id == account_id, Purchase.user_id == current_user.id) \
                                  .order_by(Purchase.purchase_date.desc()) \
                                  .first()
    last_purchase_date = last_purchase.purchase_date if last_purchase else None

    if request.method == 'POST':
        if 'submit_purchase' in request.form:
            transaction_id = uuid4()  # Generate a unique transaction ID

            for key, value in request.form.items():
                if key.startswith('quantity_'):
                    ticker = key.split('_')[1]
                    quantity = int(value)
                    
                    stock = Stock.query.filter_by(account_id=account.id, ticker=ticker).first()
                    if stock:
                        stock.quantity += quantity
                    else:
                        new_stock = Stock(ticker=ticker, quantity=quantity, account_id=account.id)
                        db.session.add(new_stock)

                    new_purchase = Purchase(
                        user_id=current_user.id,
                        stock_id=stock.id,
                        quantity=quantity,
                        price_paid=stock.current_price,
                        purchase_date=datetime.utcnow(),
                        transaction_id=transaction_id
                    )
                    db.session.add(new_purchase)

        elif 'cash_value' in request.form:
            cash_value = float(request.form['cash_value'])
            suggested_purchases = get_suggested_purchases(account, cash_value)
            return render_template('make_purchase.html', account=account, suggested_purchases=suggested_purchases, cash_value=cash_value, last_purchase_date=last_purchase_date)

        db.session.commit()
        flash("Purchase made successfully!", 'success')
        return redirect(url_for('portfolio.view_positions', account_id=account.id))

    return render_template('make_purchase.html', account=account, last_purchase_date=last_purchase_date)

def get_suggested_purchases(account, cash_value):
    """Calculates stock purchases based on target allocation and available cash,
       prioritizing stocks furthest from their target allocation."""
    
    stocks = Stock.query.filter_by(account_id=account.id, isincluded=True).all()
    allocations = Allocation.query.filter_by(account_id=account.id).all()

    # Create a dictionary of stock allocations
    allocation_dict = {allocation.name: allocation.target for allocation in allocations}

    # Calculate total market value
    total_market_value = sum(stock.market_value for stock in stocks)

    # Calculate allocation gap and sort by highest gap first
    stock_gaps = []
    for stock in stocks:
        current_allocation = (stock.market_value / total_market_value) * 100 if total_market_value > 0 else 0
        target_allocation = allocation_dict.get(stock.ticker, 0)

        allocation_gap = target_allocation - current_allocation  # Higher gap = needs more funding
        stock_gaps.append((stock, allocation_gap))

    # Sort stocks by allocation gap (largest gap first)
    stock_gaps.sort(key=lambda x: x[1], reverse=True)

    suggested_purchases = []
    total_suggested_cost = 0.0

    # Purchase stocks starting with the biggest allocation gap
    for stock, allocation_gap in stock_gaps:
        current_price = stock.current_price
        if current_price > 0 and allocation_gap > 0:  # Ensure there's an actual gap
            target_allocation = allocation_dict.get(stock.ticker, 0) / 100
            target_value = target_allocation * (total_market_value + cash_value)
            target_quantity = int(target_value / current_price)
            max_quantity = int((cash_value - total_suggested_cost) / current_price)

            # Calculate how much should be purchased to close the gap
            quantity_to_purchase = min(target_quantity - stock.quantity, max_quantity)
            estimated_total_cost = round(quantity_to_purchase * current_price, 2)

            if quantity_to_purchase > 0 and total_suggested_cost + estimated_total_cost <= cash_value:
                suggested_purchases.append({
                    'name': stock.ticker,
                    'current_price': current_price,
                    'current_position': stock.quantity,
                    'suggested_quantity': quantity_to_purchase,
                    'estimated_total_cost': estimated_total_cost,
                })
                total_suggested_cost += estimated_total_cost

    return suggested_purchases

@portfolio_bp.route('/view_allocation/<int:account_id>')
@login_required
def view_allocation(account_id):
    """Displays the user's current stock allocations."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    included_stocks = Stock.query.filter_by(account_id=account.id, isincluded=True).all()
    total_market_value = sum(stock.market_value for stock in included_stocks)
    allocations = []

    for stock in included_stocks:
        current_allocation = (stock.market_value / total_market_value) * 100 if total_market_value > 0 else 0
        target_allocation = Allocation.query.filter_by(account_id=account.id, name=stock.ticker).first()
        allocations.append({
            'ticker': stock.ticker,
            'current_allocation': round(current_allocation, 2),
            'target_allocation': round(target_allocation.target, 2) if target_allocation else 0
        })

    return render_template('view_allocation.html', account=account, allocations=allocations)

@portfolio_bp.route('/adjust_allocation/<int:account_id>', methods=['GET', 'POST'])
@login_required
def adjust_allocation(account_id):
    """Allows users to adjust stock allocations."""
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        allocation_names = request.form.getlist('allocation_name')
        allocation_targets = request.form.getlist('allocation_target')

        print(f"allocation_names: {allocation_names}")
        print(f"allocation_targets: {allocation_targets}")

        for name, target in zip(allocation_names, allocation_targets):
            allocation = Allocation.query.filter_by(account_id=account.id, name=name).first()
            if allocation:
                allocation.target = float(target)
            else:
                new_allocation = Allocation(name=name, target=float(target), account_id=account.id)
                db.session.add(new_allocation)

        db.session.commit()
        flash("Allocations updated successfully!", 'success')
        return redirect(url_for('portfolio.view_allocation', account_id=account.id))  # ✅ Redirects after POST

    # ✅ Only runs if GET
    stocks = Stock.query.filter_by(account_id=account.id).all()
    allocations = [
        {
            'name': stock.ticker,
            'target': Allocation.query.filter_by(account_id=account.id, name=stock.ticker).first().target if Allocation.query.filter_by(account_id=account.id, name=stock.ticker).first() else 0,
            'isincluded': stock.isincluded
        } 
        for stock in stocks
    ]

    return render_template('adjust_allocation.html', account=account, allocations=allocations)  # ✅ Only runs on GET

    
@portfolio_bp.route('/view_positions/<int:account_id>', methods=['GET'])
@login_required
def view_positions(account_id):
    """Displays all positions in the user's portfolio."""
    account = Account.query.get_or_404(account_id)
    stocks = Stock.query.filter_by(account_id=account_id).all()

    stock_data_list = [
        {
            "ticker": stock.ticker,
            "quantity": stock.quantity,
            "current_price": stock.current_price,
            "market_value": stock.quantity * stock.current_price,
            "isincluded": stock.isincluded
        }
        for stock in stocks
    ]

    return render_template(
        'view_positions.html',
        account=account,
        stock_data_list=stock_data_list,
        total_market_value=sum(stock["market_value"] for stock in stock_data_list),
        included_market_value=sum(stock["market_value"] for stock in stock_data_list if stock["isincluded"]),
        tracked_market_value=sum(stock["market_value"] for stock in stock_data_list if not stock["isincluded"])
    )

@portfolio_bp.route('/edit_portfolio/<int:account_id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio(account_id):
    """Allows users to edit portfolio holdings (add, remove, update quantities)."""
    account = Account.query.get_or_404(account_id)

    if request.method == 'POST':
        stocks = request.form.getlist('tickers[]')
        quantities = request.form.getlist('quantities[]')
        new_tickers = request.form.getlist('new_tickers[]')
        new_quantities = request.form.getlist('new_quantities[]')

        # Process existing stocks
        for i, stock in enumerate(stocks):
            quantity = int(quantities[i]) if quantities[i] else 0
            isincluded = request.form.get(f'isincluded_{stock}', 'off') == 'on'  # Checkbox for "Include in Calculations"

            if request.form.get(f'delete_{stock}'):
                # Delete stock if delete button is clicked
                Stock.query.filter_by(account_id=account_id, ticker=stock).delete()
            else:
                # Update stock details
                Stock.query.filter_by(account_id=account_id, ticker=stock).update({
                    'quantity': quantity,
                    'isincluded': isincluded
                })

        # Process new stocks
        for i, ticker in enumerate(new_tickers):
            if ticker.strip():
                stock_data = yf.Ticker(ticker).info
                if 'shortName' in stock_data:
                    # Add new stock to account
                    new_stock = Stock(
                        account_id=account.id,
                        ticker=ticker.upper(),
                        quantity=int(new_quantities[i]) if new_quantities[i] else 0,
                        isincluded=True  # New stocks are included by default
                    )
                    db.session.add(new_stock)
                else:
                    flash(f"Ticker symbol {ticker} is not valid, please verify and try again.")
                    return render_template('edit_portfolio.html', account=account, stocks=Stock.query.filter_by(account_id=account_id).all())

        db.session.commit()
        flash('Portfolio updated successfully!')
        return redirect(url_for('accounts.view_account', account_id=account.id))
    
    # Initial GET request, load current stocks
    stocks = Stock.query.filter_by(account_id=account_id).all()
    return render_template('edit_portfolio.html', account=account, stocks=stocks)

@portfolio_bp.route('/validate_tickers', methods=['POST'])
@login_required
def validate_tickers():
    data = request.get_json()
    tickers = data.get('tickers', [])
    valid_tickers = []
    invalid_tickers = []

    for ticker in tickers:
        stock_data = yf.Ticker(ticker).info
        if 'shortName' in stock_data:
            valid_tickers.append(f"{ticker} - {stock_data.get('shortName', 'Unknown')}")
        else:
            invalid_tickers.append(ticker)

    if invalid_tickers:
        return jsonify(valid=False, invalid_tickers=invalid_tickers)
    else:
        return jsonify(valid=True, matches=valid_tickers)