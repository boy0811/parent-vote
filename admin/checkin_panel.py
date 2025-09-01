from flask import Blueprint, render_template, request, jsonify
from models import db, Candidate, VotePhase
from datetime import datetime

checkin_panel_bp = Blueprint('checkin_panel_bp', __name__)   # ✅ Blueprint 改名

# ✅ 班級轉年級輔助函式
def get_grade(class_name):
    if not class_name:
        return ''
    try:
        if '幼' in class_name or class_name.startswith('0'):
            return '幼兒園'
        mapping = {
            '1': '一年級',
            '2': '二年級',
            '3': '三年級',
            '4': '四年級',
            '5': '五年級',
            '6': '六年級'
        }
        return mapping.get(str(class_name)[0], '')
    except:
        return ''

# ✅ 簽到面板
@checkin_panel_bp.route('/checkin_panel', methods=['GET'])
def checkin_panel():
    phases = VotePhase.query.filter(VotePhase.id.in_([2, 3])).all()
    selected_phase_id = request.args.get('phase_id')
    selected_grade = request.args.get('grade')

    if not selected_phase_id:
        current_phase = VotePhase.query.filter_by(is_open=True).order_by(VotePhase.id).first()
        if current_phase:
            selected_phase_id = str(current_phase.id)

    query = Candidate.query
    if selected_phase_id:
        query = query.filter_by(phase_id=int(selected_phase_id))

    candidates = query.order_by(Candidate.class_name, Candidate.name).all()

    if selected_grade:
        candidates = [c for c in candidates if get_grade(c.class_name) == selected_grade]

    return render_template('checkin_panel.html',
                           candidates=candidates,
                           phases=phases,
                           selected_phase_id=selected_phase_id,
                           selected_grade=selected_grade)

# ✅ 單人簽到
@checkin_panel_bp.route('/checkin_panel/signin/<int:candidate_id>', methods=['POST'])
def checkin_panel_signin(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    candidate.is_signed_in = True
    candidate.signed_in_time = datetime.now()
    db.session.commit()
    return jsonify({'status': 'success'})

# ✅ 單人取消簽到
@checkin_panel_bp.route('/checkin_panel/uncheckin/<int:candidate_id>', methods=['POST'])
def checkin_panel_uncheckin(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    candidate.is_signed_in = False
    candidate.signed_in_time = None
    db.session.commit()
    return jsonify({'status': 'success'})


