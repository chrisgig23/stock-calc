from flask_app import app, db
from cryptography.fernet import Fernet
from flask_app.models import Account

with app.app_context():
    encryption_key = app.config['ENCRYPTION_KEY']
    f = Fernet(encryption_key)
    
    accounts = db.session.query(Account).all()  # Fetch all accounts
    for account in accounts:
        encrypted_name = f.encrypt(account.account_name.encode()).decode()
        account._account_name = encrypted_name
        db.session.add(account)
    
    db.session.commit()