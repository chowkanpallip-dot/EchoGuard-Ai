from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..forms import PasswordChangeForm, ProfileForm
from ..utils import audit, require_verified

bp = Blueprint("settings", __name__)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
@require_verified
def index():
    profile_form = ProfileForm(prefix="profile")
    password_form = PasswordChangeForm(prefix="password")
    if profile_form.submit.data and profile_form.validate_on_submit():
        current_user.name = profile_form.name.data.strip()
        db.session.commit()
        audit("profile_updated", user=current_user)
        flash("Profile updated.", "success")
        return redirect(url_for("settings.index"))
    if password_form.submit.data and password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(password_form.password.data)
            db.session.commit()
            audit("password_changed", user=current_user)
            flash("Password changed. Other sessions may remain active until they expire.", "success")
            return redirect(url_for("settings.index"))
    profile_form.name.data = current_user.name
    return render_template("settings/index.html", profile_form=profile_form, password_form=password_form)
