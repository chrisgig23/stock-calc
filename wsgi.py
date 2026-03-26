from flask_app import app, db

# Auto-create tables if they don't exist (safe for both dev and prod)
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)  # Debug mode ON for local development
