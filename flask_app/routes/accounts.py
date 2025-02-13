from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from flask_app import db
from flask_app.models import Account

accounts_bp = Blueprint('accounts', __name__)

@accounts_bp.route('/view_account', defaults={'account_id': None})
@accounts_bp.route('/view_account/<int:account_id>')
@login_required
def view_account(account_id):
    """Displays a user's account and its details."""
    accounts = Account.query.filter_by(user_id=current_user.id).all() 

    if account_id:
        account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()
    else:
        account = accounts[0] if accounts else None 

    max_position = db.session.query(db.func.max(Account.position)).filter_by(user_id=current_user.id).scalar()

    if not account:
        flash('No accounts available. Please create a new account.', 'info')
        return redirect(url_for('accounts.add_account'))

    return render_template('account_menu.html', account=account) 


@accounts_bp.route('/add_account', methods=['GET', 'POST'])
@login_required
def add_account():
    """Allows users to create a new account."""
    if request.method == 'POST':
        new_account_name = request.form['new_account']
        existing_account = Account.query.filter_by(user_id=current_user.id, account_name=new_account_name).first()
        if existing_account:
            flash('Account name already exists.', 'danger')
        else:
            new_account = Account(account_name=new_account_name, user_id=current_user.id)
            db.session.add(new_account)
            db.session.commit()
            flash('Account added successfully!', 'success')
            return redirect(url_for('accounts.view_account', account_id=new_account.id))
    return render_template('add_account.html')

# @accounts_bp.route('/remove_account/<int:account_id>', methods=['POST'])
# @login_required
# def remove_account(account_id):
#     """Removes a user’s account by ID."""
#     account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
#     if not account:
#         flash('Account not found.', 'danger')
#         return redirect(url_for('accounts.view_account'))
    
#     db.session.delete(account)
#     db.session.commit()
#     flash('Account removed successfully.', 'success')
#     return redirect(url_for('accounts.view_account'))

@accounts_bp.route('/remove_account', methods=['GET', 'POST'])
@login_required
def remove_account():
    """Removes a user’s account."""
    accounts = Account.query.filter_by(user_id=current_user.id).all()  # Fetch all user accounts
    max_position = db.session.query(db.func.max(Account.position)).filter_by(user_id=current_user.id).scalar() or 0

    if request.method == 'POST':
        account_id_to_remove = request.form.get('account_id')
        account = Account.query.filter_by(id=account_id_to_remove, user_id=current_user.id).first()
        if account:
            db.session.delete(account)
            db.session.commit()
            flash('Account removed successfully.', 'success')
        else:
            flash('Account not found.', 'error')

        return redirect(url_for('accounts.view_account'))

    return render_template('remove_account.html', accounts=accounts, max_position=max_position)

@accounts_bp.route('/reorder_accounts', methods=['POST'])
@login_required
def reorder_accounts():
    """Updates the order of user accounts based on frontend drag-and-drop."""
    data = request.json
    if not data or 'order' not in data:
        return jsonify({'error': 'Invalid request'}), 400

    try:
        for index, account_id in enumerate(data['order']):
            account = Account.query.filter_by(id=account_id, user_id=current_user.id).first()
            if account:
                account.display_order = index
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@accounts_bp.route('/account/<int:account_id>/move_up', methods=['POST'])
@login_required
def move_account_up(account_id):
    """Moves an account up in the order."""
    account = Account.query.get_or_404(account_id)

    if account.position > 0:
        # Find the account just above the current one
        account_above = Account.query.filter_by(user_id=current_user.id, position=account.position - 1).first()
        if account_above:
            # Swap positions
            account_above.position, account.position = account.position, account_above.position
            print(f"Moving {account.account_name} from position {account.position} to position {account_above.position}")
            db.session.commit()

    return redirect(url_for('accounts.view_account'))

@accounts_bp.route('/account/<int:account_id>/move_down', methods=['POST'])
@login_required
def move_account_down(account_id):
    """Moves an account down in the order."""
    account = Account.query.get_or_404(account_id)

    # Find the account just below the current one
    account_below = Account.query.filter_by(user_id=current_user.id, position=account.position + 1).first()
    if account_below:
        # Swap positions
        account_below.position, account.position = account.position, account_below.position
        print(f"Moving {account.account_name} from position {account.position} to position {account_below.position}")
        db.session.commit()

    return redirect(url_for('accounts.view_account'))