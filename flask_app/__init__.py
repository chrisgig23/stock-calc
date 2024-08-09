from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY').encode('utf-8', 'replace')
    # SECRET_KEY='30a0302980dc772f268d1ec81cec21d033398cb60c0520756b2ef3acfaa36961'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

# Initialize the app and apply the configuration
app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import the User model for the user loader
from flask_app.models import User, Account, Stock, Purchase

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # print(f"User ID passed to load_user: {user_id}")  # This will show you what's being passed
    return User.query.get(int(user_id))  # This is where it fails if user_id is not an integer

# Import routes to register them with the Flask app
from flask_app import routes