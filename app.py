import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "mysupersecret"  # directly here

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///missing.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Email setup (directly here)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "mohshinmansuri123@gmail.com"      # <== put your Gmail here
app.config["MAIL_PASSWORD"] = "uiim ptpt qwby uope"         # <== put your Gmail app password here
app.config["MAIL_DEFAULT_SENDER"] = ("FaceApp Alerts", "mohshinmansuri123@gmail.com")
mail = Mail(app)

# Upload folder
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================
# Database Models
# =========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    persons = db.relationship("MissingPerson", backref="owner", lazy=True)


class MissingPerson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default="missing")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


# =========================
# Routes
# =========================
@app.route("/")
def home():
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        persons = MissingPerson.query.filter_by(owner_id=user.id).all()
        return render_template("dashboard.html", user=user, persons=persons)
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = generate_password_hash(request.form["password"], method="pbkdf2:sha256")

        if User.query.filter_by(email=email).first():
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))


@app.route("/add_person", methods=["GET", "POST"])
def add_person():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        file = request.files["image"]

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            person = MissingPerson(name=name, age=age, image=filepath, owner_id=session["user_id"])
            db.session.add(person)
            db.session.commit()
            flash("Missing person added successfully!", "success")
            return redirect(url_for("home"))

    return render_template("add_person.html")


@app.route("/mark_found/<int:person_id>")
def mark_found(person_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    person = MissingPerson.query.get_or_404(person_id)
    person.status = "found"
    db.session.commit()

    user = User.query.get(person.owner_id)
    send_found_email(user.email, person.name)

    flash(f"{person.name} marked as found!", "success")
    return redirect(url_for("home"))


# =========================
# Email Function
# =========================
def send_found_email(user_email, person_name):
    subject = "Missing Person Found!"
    body = f"Good news! {person_name} has been found."

    msg = Message(subject=subject, recipients=[user_email], body=body)
    mail.send(msg)


# =========================
# Run
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
