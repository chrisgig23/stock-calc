from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://myuser:mypassword@localhost/mydatabase'  # Replace with your actual DB URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import the User model for the user loader
from flask_app.models import User, Account, Stock

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # print(f"User ID passed to load_user: {user_id}")  # This will show you what's being passed
    return User.query.get(int(user_id))  # This is where it fails if user_id is not an integer

# Import routes to register them with the Flask app
from flask_app import routes