from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Candidate, Vote, VotePhase, Setting
from sqlalchemy import func
import random
import traceback

admin_quickvote_bp = Blueprint('admin_quickvote', __name__)

@admin_quickvote_bp.route('/quick_vote', methods=['GET', 'POST'])
def quick_vote():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    current_phase = VotePhase.query.filter_by(is_open=True).first()
    if not current_phase:
        flash('⚠️ 尚未開啟任何投票階段', 'warning')
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        candidate = Candidate.query.get(candidate_id)

        if candidate and candidate.phase_id == current_phase.id:
            try:
                # ✅ 使用隨機 voter_id 避免 UNIQUE constraint 衝突
                voter_id = random.randint(100000, 999999)
                vote = Vote(candidate_id=candidate.id, phase_id=current_phase.id, voter_id=voter_id)
                db.session.add(vote)
                db.session.commit()

                # ✅ 計算更新後票數
                count = Vote.query.filter_by(candidate_id=candidate.id, phase_id=current_phase.id).count()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'vote_count': count})

                flash(f'✅ 已為候選人 ID {candidate_id} 成功灌票 1 票！（階段：{current_phase.name}）', 'success')
                return redirect(url_for('admin_quickvote.quick_vote'))

            except Exception as e:
                db.session.rollback()
                print("🚨 投票失敗：", e)
                traceback.print_exc()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': str(e)}), 500
                flash('⚠️ 投票失敗。', 'danger')
                return redirect(url_for('admin_quickvote.quick_vote'))

        else:
            flash('⚠️ 無效的候選人。', 'danger')
            return redirect(url_for('admin_quickvote.quick_vote'))

    # ✅ GET 方法：顯示畫面
    candidates = Candidate.query.filter_by(phase_id=current_phase.id).all()
    vote_counts = dict(
        db.session.query(
            Vote.candidate_id, func.count(Vote.id)
        ).filter_by(phase_id=current_phase.id).group_by(Vote.candidate_id).all()
    )

    grade_mapping = {
        '0': '幼兒園',
        '1': '一年級',
        '2': '二年級',
        '3': '三年級',
        '4': '四年級',
        '5': '五年級',
        '6': '六年級'
    }

    grouped_candidates = {}
    for c in candidates:
        class_prefix = c.class_name[0] if c.class_name and c.class_name[0].isdigit() else '0'
        grade = grade_mapping.get(class_prefix, '未分類')
        grouped_candidates.setdefault(grade, []).append(c)

    refresh_setting = Setting.query.filter_by(key='refresh_interval').first()
    refresh_interval = int(refresh_setting.value) if refresh_setting and refresh_setting.value.isdigit() else 10

    return render_template("admin_quick_vote.html",
                           current_phase=current_phase,
                           grouped_candidates=grouped_candidates,
                           vote_counts=vote_counts,
                           refresh_interval=refresh_interval)
