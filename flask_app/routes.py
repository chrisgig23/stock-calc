from flask import render_template, redirect, url_for, request, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from flask_app import app, db
from flask_app.models import User, Account, Position, Allocation, Stock
from flask_app.utils.price_fetcher import fetch_current_prices
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify, request
import yfinance as yf

@app.context_processor
def inject_market_state():
    ticker = yf.Ticker("AAPL")
    market_state = ticker.info.get("marketState", "CLOSED")
    # market_state = "REGULAR"
    return dict(market_state=market_state)

@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('menu'))
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            if check_password_hash(user.password_hash, 'password1'):
                # Redirect to password reset page if the user has the default password
                return redirect(url_for('reset_password', user_id=user.id))
            else:
                # Log in the user if the password is not the default
                login_user(user)
                return redirect(url_for('menu'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    logout_user()
    return redirect(url_for('login'))

from flask_login import logout_user

@app.route('/reset_password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    user = User.query.get(user_id)
    
    if not user:
        # Handle the case where the user does not exist
        flash('User does not exist.')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        if new_password == confirm_password:
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            # Log the user out after password reset
            logout_user()
            
            flash('Password has been reset successfully. Please log in with your new password.')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match. Please try again.')
    
    return render_template('reset_password.html', user=user)

@app.route('/menu', methods=['GET', 'POST'])
@login_required
def menu():
    # Fetch accounts with both name and ID
    account_objects = current_user.get_accounts()

    if request.method == 'POST':
        selected_account_id = request.form['account']
        if selected_account_id == 'add':
            return redirect(url_for('add_account'))
        elif selected_account_id == 'remove':
            if len(account_objects)>0:
                return redirect(url_for('remove_account'))
            else:
                flash('No accounts to remove.', 'error')
        else:
            return redirect(url_for('view_account', account_id=selected_account_id))
    
    
    
    # Create a list of dictionaries with account name and ID
    accounts = [{"account_name": account.account_name, "account_id": account.id} for account in account_objects]
    
    return render_template('menu.html', accounts=accounts)

@app.route('/add_account', methods=['GET', 'POST'])
@login_required
def add_account():
    if request.method == 'POST':
        new_account_name = request.form['new_account']

        # Check if the account name already exists for this user
        existing_account = Account.query.filter_by(user_id=current_user.id, account_name=new_account_name).first()
        if existing_account:
            flash('Account name already exists. Please choose a different name.', 'error')
            return redirect(url_for('add_account'))

        # Create and add the new account
        new_account = Account(account_name=new_account_name, user_id=current_user.id)
        db.session.add(new_account)
        db.session.commit()

        flash('Account added successfully!', 'success')
        return redirect(url_for('menu'))
    
    return render_template('add_account.html')

@app.route('/remove_account', methods=['GET', 'POST'])
@login_required
def remove_account():
    if request.method == 'POST':
        account_id_to_remove = request.form['account_id']
        account = Account.query.filter_by(id=account_id_to_remove, user_id=current_user.id).first()
        if account:
            db.session.delete(account)
            db.session.commit()
            flash('Account removed successfully.', 'success')
        else:
            flash('Account not found or does not belong to you.', 'error')

        return redirect(url_for('menu'))

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    return render_template('remove_account.html', accounts=accounts)

@app.route('/view_account/<int:account_id>')
@login_required
def view_account(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    return render_template('account_menu.html', account=account)

@app.route('/make_purchase/<int:account_id>', methods=['GET', 'POST'])
@login_required
def make_purchase(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    total_target_allocation = db.session.query(db.func.sum(Allocation.target)).filter_by(account_id=account_id).scalar() or 0

    if total_target_allocation != 100:
        flash("Please set desired allocation before making a purchase.")
        return redirect(url_for('adjust_allocation', account_id=account_id))

    if request.method == 'POST':
        if 'submit_purchase' in request.form:
            # Second step: user confirms the purchase
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
        elif 'cash_value' in request.form:
            # First step: user entered cash value, show suggested purchases
            cash_value = float(request.form['cash_value'])
            suggested_purchases = get_suggested_purchases(account, cash_value)
            return render_template('make_purchase.html', account=account, suggested_purchases=suggested_purchases, cash_value=cash_value)


        db.session.commit()
        flash("Purchase made successfully!")
        return redirect(url_for('view_positions', account_id=account.id))

    # Initial GET request or no cash value provided
    return render_template('make_purchase.html', account=account)


def get_suggested_purchases(account, cash_value):
    # Fetch all stocks and their allocations
    stocks = Stock.query.filter_by(account_id=account.id).all()
    allocations = Allocation.query.filter_by(account_id=account.id).all()

    # Create a dictionary of allocations indexed by stock name
    allocation_dict = {allocation.name: allocation.target for allocation in allocations}

    # Calculate the total market value of the account
    total_market_value = sum(stock.market_value for stock in stocks)

    suggested_purchases = []
    total_suggested_cost = 0.0

    for stock in stocks:
        current_price = stock.current_price

        if current_price > 0:
            # Get the target allocation percentage for the stock
            target_allocation = allocation_dict.get(stock.ticker, 0) / 100

            # Calculate the target value based on the current cash value and total market value
            target_value = target_allocation * (total_market_value + cash_value)

            # Calculate the quantity needed to reach the target allocation
            target_quantity = int(target_value / current_price)

            # Calculate the quantity to purchase within the remaining cash value
            max_quantity = int((cash_value - total_suggested_cost) / current_price)
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


@app.route('/view_allocation/<int:account_id>')
@login_required
def view_allocation(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    
    # Fetch all stocks in the account
    stocks = Stock.query.filter_by(account_id=account.id).all()

    # Initialize variables
    total_market_value = 0
    allocations = []

    # Calculate the total market value and collect allocation data
    for stock in stocks:
        total_market_value += stock.market_value

    # Calculate the current allocation as a percentage of the total market value
    for stock in stocks:
        current_allocation = (stock.market_value / total_market_value) * 100 if total_market_value > 0 else 0
        target_allocation = Allocation.query.filter_by(account_id=account.id, name=stock.ticker).first()
        allocations.append({
            'ticker': stock.ticker,
            'current_allocation': round(current_allocation, 2),
            'target_allocation': round(target_allocation.target, 2) if target_allocation else 0
        })

    return render_template('view_allocation.html', account=account, allocations=allocations)

@app.route('/adjust_allocation/<int:account_id>', methods=['GET', 'POST'])
@login_required
def adjust_allocation(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    if request.method == 'POST':
        allocation_names = request.form.getlist('allocation_name')
        allocation_targets = request.form.getlist('allocation_target')

        for name, target in zip(allocation_names, allocation_targets):
            allocation = Allocation.query.filter_by(account_id=account.id, name=name).first()
            if allocation:
                allocation.target = float(target)
            else:
                new_allocation = Allocation(name=name, target=float(target), account_id=account.id)
                db.session.add(new_allocation)

        db.session.commit()
        flash("Allocations updated successfully!")
        return redirect(url_for('view_allocation', account_id=account.id))

    # Retrieve all stocks for the account
    stocks = Stock.query.filter_by(account_id=account.id).all()

    # Ensure all stocks have an allocation
    allocations = []
    for stock in stocks:
        allocation = Allocation.query.filter_by(account_id=account.id, name=stock.ticker).first()
        if allocation:
            allocations.append(allocation)
        else:
            allocations.append(Allocation(name=stock.ticker, target=0, account_id=account.id))

    return render_template('adjust_allocation.html', account=account, allocations=allocations)

@app.route('/view_positions/<account_id>')
@login_required
def view_positions(account_id):
    account = Account.query.get_or_404(account_id)
    stocks = Stock.query.filter_by(account_id=account_id).all()
    
    if not stocks:
        flash('No stocks found in this account.')
        return redirect(url_for('menu'))  # Redirect to menu if no stocks are found

    stock_data_list = []
    total_market_value = 0

    for stock in stocks:
        # Using the properties directly from the Stock model
        current_price = stock.current_price
        market_value = stock.market_value
        total_market_value += market_value

        stock_data_list.append({
            'ticker': stock.ticker,
            'quantity': stock.quantity,
            'current_price': current_price,
            'market_value': market_value
        })
    
    return render_template('view_positions.html', account=account, stock_data_list=stock_data_list,total_market_value=total_market_value)
# Replaced with Edit Portfolio
# @app.route('/adjust_positions/<account_name>', methods=['GET', 'POST'])
# @login_required
# def adjust_positions(account_name):
#     account = Account.query.filter_by(user_id=current_user.id, name=account_name).first()
#     positions = Position.query.filter_by(account_id=account.id).all()
#     prices = fetch_current_prices(positions)
#     if request.method == 'POST':
#         for position in positions:
#             new_quantity = int(request.form.get(f'quantity_{position.name}', 0))
#             position.quantity = new_quantity
#         db.session.commit()
#         return redirect(url_for('view_positions', account_name=account_name))
#     return render_template('adjust_positions.html', account_name=account_name, positions=positions, prices=prices)

@app.route('/edit_portfolio/<account_id>', methods=['GET', 'POST'])
@login_required
def edit_portfolio(account_id):
    account = Account.query.get_or_404(account_id)
    
    if request.method == 'POST':
        stocks = request.form.getlist('tickers[]')
        quantities = request.form.getlist('quantities[]')
        new_tickers = request.form.getlist('new_tickers[]')
        new_quantities = request.form.getlist('new_quantities[]')

        # Process existing stocks
        for i, stock in enumerate(stocks):
            quantity = quantities[i]
            if request.form.get(f'delete_{stock}'):
                Stock.query.filter_by(account_id=account_id, ticker=stock).delete()
            else:
                Stock.query.filter_by(account_id=account_id, ticker=stock).update({'quantity': quantity})

        # Process new stocks
        for i, ticker in enumerate(new_tickers):
            if ticker:
                stock_data = yf.Ticker(ticker).info
                if 'shortName' in stock_data:
                    # Add new stock to account
                    new_stock = Stock(account_id=account.id, ticker=ticker, quantity=int(new_quantities[i]) if new_quantities[i] else 0)
                    db.session.add(new_stock)
                else:
                    flash(f"Ticker symbol {ticker} is not valid, please verify and try again.")
                    return render_template('edit_portfolio.html', account=account, stocks=Stock.query.filter_by(account_id=account_id).all())

        db.session.commit()
        flash('Portfolio updated successfully!')
        return redirect(url_for('view_account', account_id=account.id))

    # Initial GET request, load current stocks
    stocks = Stock.query.filter_by(account_id=account_id).all()
    return render_template('edit_portfolio.html', account=account, stocks=stocks)

@app.route('/validate_tickers', methods=['POST'])
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