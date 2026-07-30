"""
app.py
------
Main Flask application for the College Event Management System.

Run with:
    python app.py

This file contains:
  - App & database configuration
  - Authentication routes (register / login / logout)
  - Dashboard route
  - Event CRUD routes (create / read / update / delete)
  - Search & filter logic
  - Image upload handling
"""

import os
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from models import db, User, Event

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "college-event-management-secret-key"  # used to sign session cookies
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(BASE_DIR, "database.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB max upload size

db.init_app(app)

# Make sure the uploads folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def allowed_file(filename):
    """Check that the uploaded file has an allowed image extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(view_func):
    """Decorator that redirects to the login page if the user isn't logged in."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


def current_user():
    """Return the User object for the currently logged-in user, or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


@app.context_processor
def inject_user():
    """Makes `current_user` available inside every template automatically."""
    return {"current_user": current_user()}


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    # Show the 6 most recently created events on the landing page
    latest_events = Event.query.order_by(Event.created_at.desc()).limit(6).all()
    total_events = Event.query.count()
    return render_template("index.html", events=latest_events, total_events=total_events)


# ---------------------------------------------------------------------------
# Authentication: Register
# ---------------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # ---- Validation ----
        errors = []
        if not username or not email or not password:
            errors.append("All fields are required.")
        if password != confirm_password:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", username=username, email=email)

        # ---- Create the user with a securely hashed password ----
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------------------------------------------------------------------
# Authentication: Login
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ---------------------------------------------------------------------------
# Authentication: Logout
# ---------------------------------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    today = date.today()

    total_events = Event.query.count()
    upcoming_events = Event.query.filter(Event.date >= today).count()
    my_events = Event.query.filter_by(user_id=user.id).order_by(Event.date.asc()).all()

    return render_template(
        "dashboard.html",
        user=user,
        total_events=total_events,
        upcoming_events=upcoming_events,
        my_events=my_events,
        today=today,
    )


# ---------------------------------------------------------------------------
# Events listing page (search + filters)
# ---------------------------------------------------------------------------
@app.route("/events")
def events():
    query = Event.query

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    filter_type = request.args.get("filter", "").strip()

    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            db.or_(
                Event.name.ilike(like_pattern),
                Event.category.ilike(like_pattern),
                Event.organizer.ilike(like_pattern),
                Event.venue.ilike(like_pattern),
            )
        )

    if category:
        query = query.filter(Event.category == category)

    today = date.today()
    if filter_type == "upcoming":
        query = query.filter(Event.date >= today)
    elif filter_type == "completed":
        query = query.filter(Event.date < today)
    elif filter_type == "today":
        query = query.filter(Event.date == today)

    # Newest events first
    all_events = query.order_by(Event.created_at.desc()).all()

    # For the category filter dropdown, list every distinct category in use
    categories = [c[0] for c in db.session.query(Event.category).distinct().all()]

    return render_template(
        "events.html",
        events=all_events,
        categories=categories,
        search=search,
        selected_category=category,
        filter_type=filter_type,
        today=today,
    )


# ---------------------------------------------------------------------------
# Event details page
# ---------------------------------------------------------------------------
@app.route("/event/<int:event_id>")
def event_details(event_id):
    event = Event.query.get_or_404(event_id)
    is_owner = "user_id" in session and session["user_id"] == event.user_id
    return render_template("event_details.html", event=event, is_owner=is_owner, today=date.today())


# ---------------------------------------------------------------------------
# Create event
# ---------------------------------------------------------------------------
@app.route("/event/create", methods=["GET", "POST"])
@login_required
def create_event():
    if request.method == "POST":
        form = request.form
        image_file = request.files.get("image")

        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        category = form.get("category", "").strip()
        venue = form.get("venue", "").strip()
        date_str = form.get("date", "").strip()
        time_str = form.get("time", "").strip()
        organizer = form.get("organizer", "").strip()
        registration_link = form.get("registration_link", "").strip()

        # ---- Validation ----
        errors = []
        if not all([name, description, category, venue, date_str, time_str, organizer]):
            errors.append("Please fill in all required fields.")

        event_date = None
        event_time = None
        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Please provide a valid date.")

        try:
            event_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            errors.append("Please provide a valid time.")

        image_filename = None
        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                # Prefix with a timestamp so filenames never collide
                safe_name = secure_filename(image_file.filename)
                image_filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
                image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
            else:
                errors.append("Image must be a PNG, JPG, JPEG, GIF, or WEBP file.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("create_event.html", form=form)

        new_event = Event(
            name=name,
            description=description,
            category=category,
            venue=venue,
            date=event_date,
            time=event_time,
            organizer=organizer,
            image_filename=image_filename,
            registration_link=registration_link or None,
            user_id=session["user_id"],
        )
        db.session.add(new_event)
        db.session.commit()

        flash("Event created successfully!", "success")
        return redirect(url_for("event_details", event_id=new_event.id))

    return render_template("create_event.html", form={})


# ---------------------------------------------------------------------------
# Edit event
# ---------------------------------------------------------------------------
@app.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != session["user_id"]:
        abort(403)

    if request.method == "POST":
        form = request.form
        image_file = request.files.get("image")

        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        category = form.get("category", "").strip()
        venue = form.get("venue", "").strip()
        date_str = form.get("date", "").strip()
        time_str = form.get("time", "").strip()
        organizer = form.get("organizer", "").strip()
        registration_link = form.get("registration_link", "").strip()

        errors = []
        if not all([name, description, category, venue, date_str, time_str, organizer]):
            errors.append("Please fill in all required fields.")

        try:
            event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            errors.append("Please provide a valid date.")
            event_date = event.date

        try:
            event_time = datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            errors.append("Please provide a valid time.")
            event_time = event.time

        if image_file and image_file.filename:
            if allowed_file(image_file.filename):
                safe_name = secure_filename(image_file.filename)
                new_filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
                image_file.save(os.path.join(app.config["UPLOAD_FOLDER"], new_filename))
                event.image_filename = new_filename
            else:
                errors.append("Image must be a PNG, JPG, JPEG, GIF, or WEBP file.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("edit_event.html", event=event)

        event.name = name
        event.description = description
        event.category = category
        event.venue = venue
        event.date = event_date
        event.time = event_time
        event.organizer = organizer
        event.registration_link = registration_link or None

        db.session.commit()
        flash("Event updated successfully!", "success")
        return redirect(url_for("event_details", event_id=event.id))

    return render_template("edit_event.html", event=event)


# ---------------------------------------------------------------------------
# Delete event
# ---------------------------------------------------------------------------
@app.route("/event/<int:event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    if event.user_id != session["user_id"]:
        abort(403)

    # Remove the stored image file too, if it exists
    if event.image_filename:
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], event.image_filename)
        if os.path.exists(image_path):
            os.remove(image_path)

    db.session.delete(event)
    db.session.commit()
    flash("Event deleted successfully.", "info")
    return redirect(url_for("dashboard"))


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Creates database.db and all tables if they don't exist yet
    app.run(debug=True)
