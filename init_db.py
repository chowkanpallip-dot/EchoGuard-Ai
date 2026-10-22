from run import app
from echoguard.extensions import db

with app.app_context():
    db.create_all()
    print("EchoGuard database tables are ready.")
