# init_db.py
from app import app
from models import db, Admin

with app.app_context():
    db.create_all()
    print("✅ 資料庫已重建並套用 models.py 的所有欄位")

    # 建立預設管理員帳號
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('admin123')  # 預設密碼
        db.session.add(admin)
        db.session.commit()
        print("✅ 已建立預設管理員帳號：admin / admin123")
    else:
        print("ℹ️ 預設管理員帳號已存在，略過建立")
