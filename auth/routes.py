from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Candidate, User, VotePhase, Vote, Setting
from utils.helpers import get_grade_from_class, get_setting, group_candidates_by_grade
from sqlalchemy import func

auth_bp = Blueprint('auth', __name__)

# ----------------------
# 📌 取得家長投票標題
# ----------------------
def get_parent_vote_title():
    setting = Setting.query.filter_by(key='parent_vote_title').first()
    return setting.value if setting else '家長投票'

# ----------------------
# ⏲️ 取得當前開啟的階段
# ----------------------
def get_current_phase():
    return VotePhase.query.filter_by(is_open=True).first()

# ----------------------
# 🔍 判斷是否具備投票資格
# ----------------------
def is_qualified_voter(candidate, current_phase):
    if not current_phase or not candidate:
        return False

    first_phase_id = db.session.query(func.min(VotePhase.id)).scalar()
    if not first_phase_id:
        return False

    # 第一階段：所有帳號都能投票
    if current_phase.id == first_phase_id:
        return True

    # 第二、三階段：必須為第一階段晉級者 + 簽到
    first_phase_promoted = Candidate.query.filter_by(
        id=candidate.id,
        phase_id=first_phase_id,
        is_promoted=True
    ).first()

    return first_phase_promoted is not None and candidate.is_signed_in

# ----------------------
# 🏠 首頁
# ----------------------
@auth_bp.route('/')
def home():
    return render_template('index.html')

# ----------------------
# 🔑 登入
# ----------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            flash('帳號或密碼錯誤，請確認後再試。', 'danger')
            return redirect(url_for('auth.login'))

        # ✅ 登入成功
        session['user_id'] = user.id
        session['role'] = 'voter'   # 標記身份

        return redirect(url_for('auth.vote'))  # 直接導向投票頁

    return render_template('login.html')

# ----------------------
# ✍ 候選人資料確認
# ----------------------
@auth_bp.route('/confirm_candidate', methods=['GET', 'POST'], endpoint='confirm_candidate')
def confirm_candidate():
    candidate_id = session.get('voter_candidate_id')
    if not candidate_id:
        return redirect(url_for('auth.login'))

    candidate = Candidate.query.get(candidate_id)

    if request.method == 'POST':
        candidate.class_name = request.form.get('class_name')
        candidate.parent_name = request.form.get('parent_name')
        db.session.commit()
        return redirect(url_for('auth.candidate_dashboard'))

    return render_template('confirm.html', candidate=candidate)

# ----------------------
# 📊 候選人主頁
# ----------------------
def get_first_phase_id():
    return db.session.query(func.min(VotePhase.id)).scalar()

@auth_bp.route('/dashboard', endpoint='candidate_dashboard')
def candidate_dashboard():
    if 'voter_candidate_id' not in session:
        return redirect(url_for('auth.login'))

    candidate = Candidate.query.get(session['voter_candidate_id'])

    # 資料不完整 → 跳補資料頁
    if not candidate.class_name or not candidate.parent_name:
        return redirect(url_for('auth.confirm_candidate'))

    current_phase = get_current_phase()
    first_phase_id = get_first_phase_id()

    promoted = False
    if first_phase_id:
        promoted = Candidate.query.filter_by(
            id=candidate.id,
            phase_id=first_phase_id,
            is_promoted=True
        ).first() is not None

    needs_checkin = current_phase and current_phase.id != first_phase_id and promoted and not candidate.is_signed_in

    can_vote = False
    if current_phase:
        if current_phase.id == first_phase_id:
            can_vote = True
        else:
            can_vote = promoted and candidate.is_signed_in

    return render_template(
        "candidate_dashboard.html",
        candidate=candidate,
        current_phase=current_phase,
        can_vote=can_vote,
        promoted=promoted,
        needs_checkin=needs_checkin,
        first_phase_id=first_phase_id
    )

# ----------------------
# 📌 簽到
# ----------------------
@auth_bp.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if 'voter_candidate_id' not in session:
        return redirect(url_for('auth.login'))

    candidate = Candidate.query.get(session['voter_candidate_id'])

    if request.method == 'POST':
        candidate.is_signed_in = True
        db.session.commit()
        flash('✅ 簽到成功！', 'success')
        return redirect(url_for('auth.candidate_dashboard'))

    return render_template('checkin.html', candidate=candidate)

# ----------------------
# 🗳️ 投票
# ----------------------
@auth_bp.route('/vote', methods=['GET', 'POST'], endpoint='vote')
def vote():
    user_id = session.get('user_id')
    if not user_id:
        flash("請先登入", "danger")
        return redirect(url_for('auth.login'))

    current_phase = get_current_phase()
    if not current_phase:
        flash("⚠️ 目前尚未開啟投票階段", "warning")
        return redirect(url_for('auth.login'))

    # 🔹 強制簽到檢查（第二、第三階段必須簽到）
    first_phase_id = get_first_phase_id()
    if first_phase_id and current_phase.id > first_phase_id:
        user = User.query.get(user_id)
        if not user or not user.is_signed_in:
            flash("⚠️ 本階段必須先簽到才能投票", "warning")
            return redirect(url_for('auth.checkin'))

    vote_title = get_setting("vote_title", default="家長投票", use_cache=False)
    max_votes = current_phase.max_votes or 0
    min_votes = getattr(current_phase, 'min_votes', 1) or 1

    existing_vote_count = Vote.query.filter_by(voter_id=user_id, phase_id=current_phase.id).count()
    if existing_vote_count > 0:
        return render_template(
            "already_voted.html",
            vote_title=vote_title,
            phase=current_phase,
            max_votes=max_votes
        )

    if request.method == 'POST':
        selected_ids = request.form.getlist('candidate_ids')
        if len(selected_ids) < min_votes:
            flash(f"至少要投 {min_votes} 票", "danger")
            return redirect(url_for('auth.vote'))
        if len(selected_ids) > max_votes:
            flash(f"最多只能投 {max_votes} 票", "danger")
            return redirect(url_for('auth.vote'))

        for cid in selected_ids:
            vote = Vote(candidate_id=int(cid), voter_id=user_id, phase_id=current_phase.id)
            db.session.add(vote)

        db.session.commit()
        flash("✅ 投票完成，感謝您的參與", "success")
        return render_template(
            "already_voted.html",
            vote_title=vote_title,
            phase=current_phase,
            max_votes=max_votes
        )

    candidates = Candidate.query.filter_by(phase_id=current_phase.id).all()
    grouped_candidates = group_candidates_by_grade(candidates)
    return render_template(
        "vote.html",
        grouped_candidates=grouped_candidates,
        vote_title=vote_title,
        phase=current_phase,
        max_votes=max_votes,
        min_votes=min_votes
    )

# ----------------------
# ✅ 投票完成頁
# ----------------------
@auth_bp.route('/vote_success')
def vote_success():
    if 'voter_candidate_id' not in session:
        return redirect(url_for('auth.login'))

    candidate = Candidate.query.get(session['voter_candidate_id'])
    current_phase = get_current_phase()
    vote_title = get_parent_vote_title()

    existing_vote = Vote.query.filter_by(voter_id=candidate.id, phase_id=current_phase.id).first() if current_phase else None

    if not existing_vote:
        flash("⚠️ 尚未投票，無法查看成功頁面", "warning")
        return redirect(url_for('auth.candidate_dashboard'))

    return render_template('vote_success.html', vote_title=vote_title, current_phase=current_phase)

# ----------------------
# 📢 公開票數 API
# ----------------------
@auth_bp.route('/public_votes_api', endpoint='public_votes_api')
def public_votes_api():
    current_phase = get_current_phase()
    if not current_phase:
        return jsonify({"candidates": []})

    results = db.session.query(
        Candidate.id,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == current_phase.id)
    ).filter(
        Candidate.phase_id == current_phase.id
    ).group_by(Candidate.id).all()

    data = [{"id": cid, "votes": vote_count} for cid, vote_count in results]
    return jsonify({"candidates": data})
