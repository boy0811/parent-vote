from flask import Blueprint, render_template, redirect, url_for, request, session, flash
from models import db, Candidate, Vote, VotePhase

vote_bp = Blueprint('vote', __name__)

@vote_bp.route('/vote', methods=['GET', 'POST'])
def vote():
    if 'candidate_id' not in session:
        return redirect(url_for('auth.login'))

    candidate_id = session['candidate_id']
    candidate = Candidate.query.get(candidate_id)
    current_phase = VotePhase.query.filter_by(status='open').first()

    if not current_phase:
        flash("目前尚未開放投票階段", "warning")
        return redirect(url_for('auth.candidate_dashboard'))

    # 是否已投票
    existing_votes = Vote.query.filter_by(voter_id=candidate_id, phase=current_phase.id).all()
    voted = len(existing_votes) > 0

    if request.method == 'POST' and not voted:
        selected_ids = request.form.getlist('candidate_ids[]')
        max_votes = current_phase.max_votes
        if len(selected_ids) > max_votes:
            flash(f"最多只能投 {max_votes} 票", "danger")
        else:
            for cid in selected_ids:
                vote = Vote(voter_id=candidate_id, candidate_id=int(cid), phase=current_phase.id)
                db.session.add(vote)
            db.session.commit()
            flash("投票成功", "success")
            return redirect(url_for('vote.vote'))

    # 候選人分頁與取得
    page = request.args.get("page", 1, type=int)
    candidates_query = Candidate.query.filter_by(phase=current_phase.id).order_by(Candidate.class_name.asc())
    pagination = candidates_query.paginate(page=page, per_page=100)
    candidates = pagination.items

    # 候選人依年級分組
    grade_map = {
        '1': '一年級', '2': '二年級', '3': '三年級',
        '4': '四年級', '5': '五年級', '6': '六年級',
    }
    grouped_candidates = {
        '幼兒園': [],
        '一年級': [],
        '二年級': [],
        '三年級': [],
        '四年級': [],
        '五年級': [],
        '六年級': [],
    }

    for c in candidates:
        class_str = str(c.class_name)
        if class_str.isdigit() and 1 <= int(class_str) <= 20:
            grouped_candidates['幼兒園'].append(c)
        elif class_str and class_str[0] in grade_map:
            grouped_candidates[grade_map[class_str[0]]].append(c)

    return render_template(
        "vote.html",
        phase=current_phase,
        phase_info=current_phase,
        candidates=candidates,
        voted=voted,
        pagination=pagination,
        grouped_candidates=grouped_candidates
    )
