from app import app, db
from models import Admin

with app.app_context():
    username = 'admin'
    password = 'admin'

    admin = Admin.query.filter_by(username=username).first()

    if admin:
        admin.set_password(password)
        db.session.commit()
        print(f'✅ 管理員帳號 "{username}" 密碼已成功重設為：{password}')
    else:
        admin = Admin(username=username)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f'✅ 管理員帳號 "{username}" 已建立，密碼：{password}')
