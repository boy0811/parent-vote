# checkin/checkin_panel.py
from flask import Blueprint, render_template, request, jsonify, session, abort
from functools import wraps
from datetime import datetime
from models import db, Candidate, VotePhase

# 統一用 /checkin_panel 作為 url_prefix
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
# 年級轉換（001~020 => 幼兒園；其餘用第一碼對應 1~6 年級）
# -------------------------------------------------
def get_grade(class_name: str) -> str:
    if not class_name:
        return ''
    s = str(class_name).strip()

    # 純數字情況
    if s.isdigit():
        num = int(s)
        if 1 <= num <= 20:
            return '幼兒園'
        first = s[0]
    else:
        # 文字中帶有「幼」
        if '幼' in s:
            return '幼兒園'
        first = s[0]

    mapping = {
        '1': '一年級',
        '2': '二年級',
        '3': '三年級',
        '4': '四年級',
        '5': '五年級',
        '6': '六年級'
    }
    return mapping.get(first, '')

# -------------------------------------------------
# 簽到面板
# -------------------------------------------------
@checkin_panel_bp.route('/', methods=['GET'])
@staff_or_admin_required
def panel():
    # 如果你只允許 2、3 階段參與簽到，保留這行；若要所有階段都可簽到，改成 VotePhase.query.all()
    phases = VotePhase.query.filter(VotePhase.id.in_([2, 3])).order_by(VotePhase.id).all()

    selected_phase_id = request.args.get('phase_id', type=int)
    selected_grade = request.args.get('grade', type=str, default='')

    # 若未指定 phase_id，優先抓目前 is_open=True 的階段
    if not selected_phase_id:
        current_phase = VotePhase.query.filter_by(is_open=True).order_by(VotePhase.id).first()
        if current_phase:
            selected_phase_id = current_phase.id

    q = Candidate.query
    if selected_phase_id:
        q = q.filter(Candidate.phase_id == selected_phase_id)

    candidates = q.order_by(Candidate.class_name.asc(), Candidate.name.asc()).all()

    # 年級過濾
    if selected_grade:
        candidates = [c for c in candidates if get_grade(c.class_name) == selected_grade]

    return render_template(
        'checkin_panel.html',
        candidates=candidates,
        phases=phases,
        selected_phase_id=selected_phase_id,
        selected_grade=selected_grade
    )

# -------------------------------------------------
# 簽到
# -------------------------------------------------
@checkin_panel_bp.route('/signin/<int:candidate_id>', methods=['POST'])
@staff_or_admin_required
def signin(candidate_id):
    c = Candidate.query.get_or_404(candidate_id)
    try:
        c.is_signed_in = True
        c.signed_in_time = datetime.now()
        db.session.commit()
        return jsonify({
            'status': 'success',
            'signed_in_time': c.signed_in_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

# -------------------------------------------------
# 取消簽到
# -------------------------------------------------
@checkin_panel_bp.route('/uncheckin/<int:candidate_id>', methods=['POST'])
@staff_or_admin_required
def uncheckin(candidate_id):
    c = Candidate.query.get_or_404(candidate_id)
    try:
        c.is_signed_in = False
        c.signed_in_time = None
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

from flask import redirect, url_for

@checkin_panel_bp.app_errorhandler(403)
def handle_403(e):
    # 依你的登入頁決定要導去哪個
    return redirect(url_for('staff.staff_login'))
