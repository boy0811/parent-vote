from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 初始化 SQLAlchemy 實例
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # 設定相關參數
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///voting.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 初始化資料庫與遷移
    db.init_app(app)
    migrate.init_app(app, db)

    # 載入資料模型
    from .models import candidate, vote, admin, vote_phase, setting

    # 載入路由
    from .routes import main_routes, admin_routes, candidate_routes
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(admin_routes.bp)
    app.register_blueprint(candidate_routes.bp)

    return app
