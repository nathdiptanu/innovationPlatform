from bson import ObjectId
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import collection
from .entitlements import home_for_user, load_current_user


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.before_app_request
def before_request():
    load_current_user()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        user = collection("users").find_one({"username": username, "active": True})
        if user and check_password_hash(user["password_hash"], request.form.get("password", "")):
            session.clear()
            session["user_id"] = str(user["_id"])
            session.permanent = True
            return redirect(request.args.get("next") or home_for_user(user))
        flash("Login failed. Check the username and password.", "error")
    return render_template("auth/login.html")


@auth_bp.get("/logout")
def logout():
    session.clear()
    flash("You are logged out.", "success")
    return redirect(url_for("public.home"))
