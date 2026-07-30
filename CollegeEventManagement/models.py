"""
models.py
----------
Defines the SQLite database structure using SQLAlchemy ORM.
Two tables are created automatically the first time the app runs:
    1. User  -> stores registered users (with hashed passwords)
    2. Event -> stores college events, each linked to the user who created it
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# db is created here (not in app.py) so both app.py and models.py can share
# the same SQLAlchemy instance without circular imports.
db = SQLAlchemy()


class User(db.Model):
    """Represents a registered user (student/organizer) who can log in."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # We NEVER store the raw password — only a secure hash of it.
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One user can create many events. If a user is deleted, their events
    # are deleted too (cascade), keeping the database consistent.
    events = db.relationship(
        "Event", backref="creator", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Event(db.Model):
    """Represents a single college event created by a user."""
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    venue = db.Column(db.String(150), nullable=False)
    date = db.Column(db.Date, nullable=False)          # stored as a real Date
    time = db.Column(db.Time, nullable=False)           # stored as a real Time
    organizer = db.Column(db.String(120), nullable=False)
    # Only the filename is stored in the DB; the actual image file lives in
    # static/uploads/. This keeps the database small and fast.
    image_filename = db.Column(db.String(255), nullable=True)
    registration_link = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key linking this event to the user who created it.
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Event {self.name}>"
