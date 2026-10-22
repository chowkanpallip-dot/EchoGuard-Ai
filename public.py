from pathlib import Path

from flask import Blueprint, current_app, redirect, render_template, send_from_directory, url_for
from flask_login import current_user

bp = Blueprint("public", __name__)


@bp.get("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("public/index.html")


@bp.get("/manus-routes.json")
def route_manifest():
    return send_from_directory(Path(current_app.root_path).parent, "manus-routes.json", mimetype="application/json")
