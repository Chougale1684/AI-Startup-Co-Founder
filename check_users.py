from app import app, db, User, IdeaHistory

with app.app_context():
    users = User.query.all()
    print(f"\n{'='*50}")
    print(f"  TOTAL USERS: {len(users)}")
    print(f"{'='*50}")
    for u in users:
        ideas = IdeaHistory.query.filter_by(user_id=u.id).count()
        print(f"  ID: {u.id} | Username: {u.username} | Email: {u.email} | Ideas: {ideas}")
    print(f"{'='*50}\n")