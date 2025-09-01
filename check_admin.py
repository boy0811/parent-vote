from app import app, db
from models import Admin

with app.app_context():
    admins = Admin.query.all()
    for admin in admins:
        print(f"帳號: {admin.username}, 密碼雜湊: {admin.password_hash}")
