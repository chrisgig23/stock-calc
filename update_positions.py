from flask_app import db
from flask_app.models import User, Account  # Import your models

def backfill_account_positions():
    # Get all users
    users = User.query.all()
    
    for user in users:
        # Get the user's accounts and order them by `id` (or any other attribute)
        accounts = Account.query.filter_by(user_id=user.id).order_by(Account.id).all()
        
        # Iterate through the user's accounts and assign an incremental position
        for position, account in enumerate(accounts, start=1):
            account.position = position  # Set position starting from 1
        
        # Commit the changes for this user
        db.session.commit()

    print("Position backfill completed for all users.")

# Run the function to backfill the positions
backfill_account_positions()