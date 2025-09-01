# run_server.py
import os
import sys
import socket

# -------------------------------------------------
# 取得本機 IP（給提示用）
# -------------------------------------------------
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# -------------------------------------------------
# PyInstaller 打包後的路徑處理
# -------------------------------------------------
def get_runtime_base_dir():
    if getattr(sys, "frozen", False):  # PyInstaller
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

BASE_DIR = get_runtime_base_dir()
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

# -------------------------------------------------
# 設定環境變數（app.py 會讀）
# -------------------------------------------------
os.environ.setdefault("SECRET_KEY", "change-me-in-production")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_DIR, 'voting.db')}")
PORT = int(os.getenv("PORT", "5000"))

# -------------------------------------------------
# 匯入 Flask app
# -------------------------------------------------
from app import app, db
from models import Admin, VotePhase

def bootstrap_first_run():
    """第一次啟動時自動初始化資料"""
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            admin = Admin(username="admin")
            admin.set_password("admin")
            db.session.add(admin)
        if not VotePhase.query.first():
            phases = [
                VotePhase(id=1, name='家長委員', max_votes=6),
                VotePhase(id=2, name='常務委員', max_votes=3),
                VotePhase(id=3, name='家長會長', max_votes=1),
            ]
            db.session.add_all(phases)
        db.session.commit()

def run():
    ip = get_local_ip()
    print("🚀 伺服器啟動中...")
    print("   管理員帳號：admin / 密碼：admin")
    print(f"   打開瀏覽器連線 → http://127.0.0.1:{PORT}")
    print(f"   或使用本機 IP 供校園網使用 → http://{ip}:{PORT}")

    # 優先用 waitress，沒裝就 fallback 到 Flask 內建 server（方便除錯）
    try:
        from waitress import serve
        serve(app, host="0.0.0.0", port=PORT)
    except ModuleNotFoundError:
        print("⚠️ 沒有安裝 waitress，改用 Flask 內建伺服器啟動（僅測試用）")
        app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    bootstrap_first_run()
    run()
