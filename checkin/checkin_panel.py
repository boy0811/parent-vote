from flask import Blueprint, render_template, request, jsonify, session, abort, redirect, url_for
from functools import wraps
from datetime import datetime
from models import db, User, VotePhase

# ✅ 統一 url_prefix
checkin_panel_bp = Blueprint('checkin_panel', __name__, url_prefix='/checkin_panel')

# -------------------------------------------------
# 權限：只有已登入的 Staff 或 Admin 才能使用
# -------------------------------------------------
def staff_or_admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'staff_id' in session or 'admin_id' in session or 'admin' in session:
            return f(*args, **kwargs)
        return abort(403)
    return wrapper

# -------------------------------------------------
# 帳號對應年級規則
# -------------------------------------------------
grade_rules = [
    (1, 3, "幼兒園"),
    (4, 33, "一年級"),
    (34, 63, "二年級"),
    (64, 93, "三年級"),
    (94, 123, "四年級"),
    (124, 153, "五年級"),
    (154, 183, "六年級"),
]

def get_grade_by_username(username: str) -> str:
    try:
        num = int(username.split("-")[1])  # 例如 wh-045 → 45
    except:
        return "未分班"

    for start, end, grade in grade_rules:
        if start <= num <= end:
            return grade
    return "未分班"


# -------------------------------------------------
# 簽到面板 → 分年級顯示帳號
# -------------------------------------------------
@checkin_panel_bp.route('/', methods=['GET'])
@staff_or_admin_required
def panel():
    # ✅ 確保重新查詢最新 User 資料
    users = db.session.query(User).order_by(User.username.asc()).all()

    # 分年級
    grade_groups = {}
    for u in users:
        grade = get_grade_by_username(u.username)
        if grade not in grade_groups:
            grade_groups[grade] = []
        grade_groups[grade].append(u)

    # ✅ 移除「0 人」的群組（例如未分班）
    grade_groups = {g: us for g, us in grade_groups.items() if len(us) > 0}

    total = len(users)
    signed_count = sum(1 for u in users if u.is_signed_in)

    current_phase = VotePhase.query.filter_by(is_open=True).order_by(VotePhase.id).first()

    return render_template(
        'checkin_panel.html',
        grade_groups=grade_groups,
        phases=VotePhase.query.all(),
        current_phase=current_phase,
        total=total,
        signed_count=signed_count
    )

# -------------------------------------------------
# 簽到
# -------------------------------------------------
@checkin_panel_bp.route('/signin/<int:user_id>', methods=['POST'])
@staff_or_admin_required
def signin(user_id):
    u = User.query.get_or_404(user_id)
    try:
        u.is_signed_in = True
        u.signed_in_time = datetime.now()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'signed_in_time': u.signed_in_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -------------------------------------------------
# 取消簽到
# -------------------------------------------------
@checkin_panel_bp.route('/uncheckin/<int:user_id>', methods=['POST'])
@staff_or_admin_required
def uncheckin(user_id):
    u = User.query.get_or_404(user_id)
    try:
        u.is_signed_in = False
        u.signed_in_time = None
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -------------------------------------------------
# 錯誤處理：未登入導向登入頁
# -------------------------------------------------
@checkin_panel_bp.app_errorhandler(403)
def handle_403(e):
    return redirect(url_for('staff.staff_login'))
