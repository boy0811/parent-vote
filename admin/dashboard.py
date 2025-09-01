from flask import Blueprint, render_template, redirect, url_for, session
from models import Candidate, Vote, VotePhase, StaffVote

admin_dashboard_bp = Blueprint('admin_dashboard', __name__, url_prefix='/admin')

# ✅ 補上這行
def get_current_phase():
    return VotePhase.query.filter_by(is_open=True).first()

# ----------------------
# 管理員主控台
# ----------------------
@admin_dashboard_bp.route('/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:  # ✅ 修正這一行
        return redirect(url_for('admin_auth.admin_login'))

    candidate_count = Candidate.query.count()
    vote_count = Vote.query.count()
    staff_vote_yes = StaffVote.query.filter_by(vote_result='贊成').count()
    staff_vote_no = StaffVote.query.filter_by(vote_result='反對').count()
    phases = VotePhase.query.all()
    current_phase = get_current_phase()

    return render_template('admin_dashboard.html',
                           candidate_count=candidate_count,
                           vote_count=vote_count,
                           agree_count=staff_vote_yes,
                           disagree_count=staff_vote_no,
                           phases=phases,
                           current_phase=current_phase)

# ----------------------
# 點名名單
# ----------------------
@admin_dashboard_bp.route('/checkin_list')
def checkin_list():
    if 'admin_id' not in session:  # ✅ 同樣修正這一行
        return redirect(url_for('admin_auth.admin_login'))

    candidates = Candidate.query.order_by(Candidate.class_name, Candidate.name).all()
    return render_template('admin_checkin_list.html', candidates=candidates)
