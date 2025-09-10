import os
import sys
import logging
import secrets

from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from admin.admin_users import admin_users_bp

from models import db, Admin, VotePhase
from utils.helpers import (
    add_log,
    zh_action_from_request,
    get_request_user,
    should_log_request
)

# -------------------------------------------------
# 靜音 werkzeug 指定路徑的請求日誌
# -------------------------------------------------
def silence_werkzeug(noisy_paths=None):
    if noisy_paths is None:
        noisy_paths = ("/admin/logs/data", "/static/", "/favicon.ico")

    class EndpointFilter(logging.Filter):
        def __init__(self, paths):
            super().__init__()
            self.paths = paths

        def filter(self, record: logging.LogRecord) -> bool:
            try:
                msg = record.getMessage()
            except Exception:
                return True
            return not any(p in msg for p in self.paths)

    wlog = logging.getLogger("werkzeug")
    for h in wlog.handlers:
        h.addFilter(EndpointFilter(noisy_paths))


# -------------------------------------------------
# 路徑工具：支援 PyInstaller 打包後的執行路徑
# -------------------------------------------------
def get_basedir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(__file__))

basedir = get_basedir()

# 確保 instance 目錄存在
instance_dir = os.path.join(basedir, "instance")
os.makedirs(instance_dir, exist_ok=True)

# -------------------------------------------------
# Flask 基本設定
# -------------------------------------------------
app = Flask(__name__, instance_path=instance_dir)

app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

# ✅ 修正 DATABASE_URL
default_sqlite = 'sqlite:///' + os.path.join(instance_dir, 'voting.db')
db_url = os.getenv("DATABASE_URL", default_sqlite)

# Render / Heroku 給的會是 postgres://，要轉成 postgresql+psycopg:// (psycopg3)
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

# 移除 Neon 給的 channel_binding 參數，避免 psycopg 斷線
if "channel_binding" in db_url:
    db_url = db_url.replace("&channel_binding=require", "")

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ 加上防 idle 斷線設定
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_pre_ping": True,
    "pool_recycle": 1800,  # 30 分鐘 recycle 連線
}

db.init_app(app)
migrate = Migrate(app, db)

# -------------------------------------------------
# 載入並註冊 Blueprints
# -------------------------------------------------
from admin.admin_logs import admin_logs_bp
from public.public_votes import public_votes_bp
from admin.auth import admin_auth_bp
from admin.dashboard import admin_dashboard_bp
from admin.candidates import admin_candidates_bp
from admin.promote import admin_promote_bp
from admin.votes import admin_votes_bp
from admin.settings import admin_settings_bp
from admin.staffs import admin_staffs_bp
from admin.quick_vote import admin_quickvote_bp
from auth import auth_bp
from staff import staff_bp
from checkin.checkin_panel import checkin_panel_bp

app.register_blueprint(public_votes_bp)
app.register_blueprint(admin_auth_bp, url_prefix='/admin')
app.register_blueprint(admin_dashboard_bp, url_prefix='/admin')
app.register_blueprint(admin_candidates_bp, url_prefix='/admin')
app.register_blueprint(admin_promote_bp, url_prefix='/admin')
app.register_blueprint(admin_votes_bp, url_prefix='/admin')
app.register_blueprint(admin_settings_bp, url_prefix='/admin')
app.register_blueprint(admin_staffs_bp, url_prefix='/admin')
app.register_blueprint(admin_quickvote_bp)
app.register_blueprint(admin_logs_bp, url_prefix='/admin')
app.register_blueprint(auth_bp)
app.register_blueprint(staff_bp, url_prefix='/staff')
app.register_blueprint(checkin_panel_bp)
app.register_blueprint(admin_users_bp, url_prefix='/admin')

# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route('/')
def home():
    if app.debug:
        print('📂 目前使用的資料庫：', db.engine.url)
    return render_template('index.html')

@app.route('/admin/phases')
def show_phases():
    phases = VotePhase.query.all()
    if not phases:
        return '<h3>❌ 沒有找到任何階段資料</h3>'
    html = '<h3>✅ 當前投票階段：</h3><ul>'
    for p in phases:
        html += f'<li>ID: {p.id}，名稱: {p.name}，可投票數: {p.max_votes}</li>'
    html += '</ul>'
    return html

# 健康檢查路由 (給 Render 用)
@app.route("/healthz")
def healthz():
    return "OK", 200

# -------------------------------------------------
# CLI commands
# -------------------------------------------------
@app.cli.command("init-admin")
def init_admin():
    """建立預設管理員帳號"""
    with app.app_context():
        username = 'admin'
        password = 'admin'
        existing_admin = Admin.query.filter_by(username=username).first()
        if existing_admin:
            print(f'⚠️ 管理員帳號 "{username}" 已存在')
        else:
            admin = Admin(username=username)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f'✅ 管理員帳號 "{username}" 已成功建立（密碼：{password}）')

@app.cli.command("init-vote-phases")
def init_vote_phases_command():
    """初始化投票階段"""
    with app.app_context():
        if VotePhase.query.count() > 0:
            print("⚠️ 已存在投票階段，不重複建立")
            return
        phases = [
            VotePhase(id=1, name='家長委員', max_votes=6),
            VotePhase(id=2, name='常務委員', max_votes=3),
            VotePhase(id=3, name='家長會長', max_votes=1)
        ]
        db.session.add_all(phases)
        db.session.commit()
        print("✅ 投票階段已初始化完成")

# -------------------------------------------------
# 自動記錄操作紀錄
# -------------------------------------------------
EXCLUDE_PREFIXES = ("/static",)
EXCLUDE_ENDPOINTS = {
    "admin_logs.view_logs",
    "admin_logs.logs_data",
    "admin_logs.export_logs_csv",
}

@app.before_request
def auto_log_post_requests():
    if not should_log_request(request, exclude_prefixes=EXCLUDE_PREFIXES, exclude_endpoints=EXCLUDE_ENDPOINTS):
        return
    user_type, user_id = get_request_user(session)
    action = zh_action_from_request(request)
    try:
        add_log(user_type, user_id, action)
    except Exception as e:
        app.logger.warning(f"⚠️ 無法寫入操作紀錄: {e}")

@app.route('/admin')
def admin_redirect():
    return redirect(url_for('admin_dashboard.admin_dashboard'))

# -------------------------------------------------
# 啟動
# -------------------------------------------------
if __name__ == '__main__':
    if app.debug:
        silence_werkzeug()
    else:
        logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
