from flask import Blueprint, render_template, jsonify
from models import Candidate, Vote, VotePhase, Setting, db
from sqlalchemy import func

public_votes_bp = Blueprint('public_votes', __name__)

# 工具：投票標題
def get_parent_vote_title():
    setting = Setting.query.filter_by(key='parent_vote_title').first()
    return setting.value if setting else '家長投票'

# 工具：目前階段
def get_current_phase():
    return VotePhase.query.filter_by(is_open=True).first()

# 工具：最近結束階段
def get_latest_phase():
    return VotePhase.query.filter_by(is_open=False).order_by(VotePhase.id.desc()).first()

# 工具：刷新秒數
def get_refresh_interval():
    setting = Setting.query.filter_by(key='refresh_interval').first()
    return int(setting.value) if setting and setting.value and setting.value.isdigit() else 10

# 工具：年級分類（API 用）
def get_grade_from_class(class_name):
    try:
        class_str = str(class_name).strip()
        if class_str in ['幼', '幼兒園']:
            return '幼兒園'
        code = int(class_str)
        if 1 <= code <= 20:
            return '幼兒園'
        elif 101 <= code <= 199:
            return '一年級'
        elif 201 <= code <= 299:
            return '二年級'
        elif 301 <= code <= 399:
            return '三年級'
        elif 401 <= code <= 499:
            return '四年級'
        elif 501 <= code <= 599:
            return '五年級'
        elif 601 <= code <= 699:
            return '六年級'
        else:
            return '其他'
    except:
        return '其他'

# ✅ 公開得票頁
@public_votes_bp.route('/public/winners', endpoint='public_winners')
def public_winners():
    current_phase = get_current_phase() or get_latest_phase()
    vote_title = get_parent_vote_title()
    refresh_interval = get_refresh_interval()

    if not current_phase:
        return render_template('public_winners.html',
                               results=[],
                               current_phase=None,
                               vote_title=vote_title,
                               refresh_interval=refresh_interval)

    results = db.session.query(
        Candidate,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == current_phase.id)
    ).filter(
        Candidate.phase_id == current_phase.id
    ).group_by(
        Candidate.id
    ).order_by(
        func.count(Vote.id).desc(), Candidate.class_name.asc()
    ).all()

    ranked_results = []
    for idx, (candidate, vote_count) in enumerate(results, start=1):
        ranked_results.append({
            'id': candidate.id,
            'class_name': candidate.class_name,
            'parent_name': candidate.parent_name,
            'vote_count': vote_count,
            'rank_number': idx
        })

    return render_template('public_winners.html',
                           results=ranked_results,
                           current_phase=current_phase,
                           vote_title=vote_title,
                           refresh_interval=refresh_interval)

# ✅ 公開 API
@public_votes_bp.route('/public/api/votes')
def public_votes_api():
    current_phase = get_current_phase()
    candidates = Candidate.query.filter_by(phase_id=current_phase.id).all() if current_phase else []
    votes = Vote.query.filter_by(phase_id=current_phase.id).all() if current_phase else []

    vote_counts = {c.id: 0 for c in candidates}
    for v in votes:
        if v.candidate_id in vote_counts:
            vote_counts[v.candidate_id] += 1

    data = [dict(
        id=c.id,
        class_name=c.class_name,
        parent_name=c.parent_name,
        votes=vote_counts.get(c.id, 0),
        grade=get_grade_from_class(c.class_name)
    ) for c in candidates]

    return jsonify({'candidates': data})
