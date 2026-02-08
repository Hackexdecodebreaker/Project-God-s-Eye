from app import app
from models import db, User

with app.app_context():
    db.create_all()
    print("Database initialized successfully. User table created if it didn't exist.")
