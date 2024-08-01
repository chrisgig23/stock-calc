from flask_app import app, db
from flask_app.models import User
from werkzeug.security import generate_password_hash

def add_user(new_username):
    with app.app_context():
        # Create a new user with a default temporary password
        user = User(username=new_username, password_hash=generate_password_hash('password1'))
        
        # Add the user to the session and commit to the database
        db.session.add(user)
        db.session.commit()

        print(f"User {new_username} added successfully with a temporary password 'password1'.")

if __name__ == '__main__':
    new_user = input("New Username: ")
    add_user(new_user)