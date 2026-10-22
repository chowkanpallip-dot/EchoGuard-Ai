from run import app
from echoguard.extensions import db
from echoguard.models import Note, Task, User

with app.app_context():
    user = User.query.filter_by(email="demo@echoguard.local").first()
    if not user:
        user = User(email="demo@echoguard.local", name="Demo User", is_verified=True)
        user.set_password("DemoPassword123!")
        db.session.add(user)
        db.session.commit()
    if not Note.query.filter_by(user_id=user.id).first():
        notes = [
            Note(user_id=user.id, title="Research outline — next steps", category="Work", content="I need to send Maya the latest research outline after lunch. The open question is how the interview notes change the second section."),
            Note(user_id=user.id, title="Weekend reset ideas", category="Personal", content="Try the new walking route on Saturday and remember to call Dad before dinner. Keep Sunday morning clear for reading."),
            Note(user_id=user.id, title="Product thoughts", category="Ideas", content="A quiet memory assistant should show where every answer came from and ask before turning a suggestion into a task."),
        ]
        db.session.add_all(notes)
        db.session.add(Task(user_id=user.id, title="Send the latest research outline", priority="high"))
        db.session.add(Task(user_id=user.id, title="Call Dad before dinner", priority="medium"))
        db.session.commit()
        print("Seeded demo data for demo@echoguard.local")
    else:
        print("Demo data already exists; no changes made.")
