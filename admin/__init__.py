from flask import Blueprint

# ✅ 建立主 Blueprint：/admin 開頭
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ✅ 匯入子 Blueprint
from .auth import admin_auth_bp
from .dashboard import admin_dashboard_bp
from .candidates import admin_candidates_bp
from .promote import admin_promote_bp
from .votes import admin_votes_bp
from .staffs import admin_staffs_bp

# ✅ 註冊子 Blueprint 到 admin_bp
admin_bp.register_blueprint(admin_auth_bp)
admin_bp.register_blueprint(admin_dashboard_bp)
admin_bp.register_blueprint(admin_candidates_bp)
admin_bp.register_blueprint(admin_promote_bp)
admin_bp.register_blueprint(admin_votes_bp)
admin_bp.register_blueprint(admin_staffs_bp)
