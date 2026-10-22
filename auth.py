from datetime import timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, limiter
from ..forms import ForgotPasswordForm, LoginForm, RegisterForm, ResetPasswordForm
from ..models import User, utcnow
from ..services.email_service import send_link_email
from ..utils import audit, consume_token, make_token, normalize_email

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = normalize_email(form.email.data)
        if User.query.filter_by(email=email).first():
            form.email.errors.append("That email is already registered. Try logging in or resetting your password.")
        else:
            user = User(email=email, name=form.name.data.strip())
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            raw = make_token(user, "verify", 24)
            delivery = send_link_email(user, "verify", raw)
            audit("registration", user=user)
            if not delivery.get("delivered") and not delivery.get("development_link"):
                flash("Account created, but email delivery is not configured. An administrator must configure SMTP before verification can complete.", "danger")
            else:
                flash("Account created. Check your email to verify it.", "success")
            if delivery.get("development_link") and current_app.config["APP_ENV"] == "development":
                return render_template("auth/verify.html", dev_link=delivery["development_link"], email=user.email)
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        if current_user.is_verified:
            return redirect(url_for("main.dashboard"))
        logout_user()
    form = LoginForm()
    dev_link = None
    if form.validate_on_submit():
        user = User.query.filter_by(email=normalize_email(form.email.data)).first()
        if user and user.is_locked:
            flash("This account is temporarily locked. Try again later.", "danger")
        elif user and user.check_password(form.password.data):
            user.failed_login_count = 0
            user.locked_until = None
            db.session.commit()
            if not user.is_verified:
                raw = make_token(user, "verify", 24)
                delivery = send_link_email(user, "verify", raw)
                dev_link = delivery.get("development_link")
                flash("Verify your email before logging in. We sent a fresh verification link.", "warning")
                if dev_link and current_app.config["APP_ENV"] == "development":
                    return render_template("auth/verify.html", dev_link=dev_link, email=user.email)
                return render_template("auth/login.html", form=form, dev_link=dev_link)
            login_user(user, remember=form.remember.data, duration=timedelta(hours=12))
            audit("login_success", user=user)
            next_url = request.args.get("next", "")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("main.dashboard")
            return redirect(next_url)
        else:
            if user:
                user.failed_login_count += 1
                if user.failed_login_count >= 5:
                    user.locked_until = utcnow() + timedelta(minutes=15)
                db.session.commit()
            audit("login_failure", user=user)
            flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form, dev_link=dev_link)


@bp.post("/logout")
@login_required
def logout():
    audit("logout", user=current_user)
    logout_user()
    flash("You are securely logged out.", "success")
    return redirect(url_for("public.index"))


@bp.get("/verify/<token>")
def verify_email(token):
    user = consume_token(token, "verify")
    if not user:
        flash("That verification link is invalid or expired.", "danger")
        return redirect(url_for("auth.login"))
    user.is_verified = True
    db.session.commit()
    audit("email_verified", user=user)
    flash("Email verified. You can now sign in.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def forgot_password():
    form = ForgotPasswordForm()
    dev_link = None
    if form.validate_on_submit():
        user = User.query.filter_by(email=normalize_email(form.email.data)).first()
        if user:
            raw = make_token(user, "reset", 1)
            delivery = send_link_email(user, "reset", raw)
            dev_link = delivery.get("development_link") if current_app.config["APP_ENV"] == "development" else None
            audit("password_reset_requested", user=user)
        flash("If an account exists for that address, a reset link has been sent.", "info")
    return render_template("auth/forgot_password.html", form=form, dev_link=dev_link)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    from hashlib import sha256
    from ..models import EmailToken
    record = EmailToken.query.filter_by(token_hash=sha256(token.encode()).hexdigest(), kind="reset", used_at=None).first()
    if not record or record.expires_at < utcnow():
        flash("That reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = consume_token(token, "reset")
        if not user:
            flash("That reset link is invalid or expired.", "danger")
            return redirect(url_for("auth.forgot_password"))
        user.set_password(form.password.data)
        user.failed_login_count = 0
        user.locked_until = None
        db.session.commit()
        audit("password_reset_completed", user=user)
        flash("Password updated. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
