from flask import Blueprint, render_template, redirect, url_for, session, flash, request, send_file, jsonify
from models import db, VotePhase, Candidate, Vote, Setting
from sqlalchemy import func
import pandas as pd
import io
from collections import OrderedDict
from utils.helpers import get_setting
from flask import jsonify

admin_votes_bp = Blueprint('admin_votes', __name__)

# ✅ 取得當前開啟階段
def get_current_phase():
    return VotePhase.query.filter_by(is_open=True).first()

# ✅ 僅抓取最新「已結束」的階段
def get_latest_phase():
    return VotePhase.query.filter_by(is_open=False).order_by(VotePhase.id.desc()).first()

def get_latest_phase_with_votes():
    # 找出已結束階段，依序找出是否有票
    closed_phases = VotePhase.query.filter_by(is_open=False).order_by(VotePhase.id.desc()).all()
    for phase in closed_phases:
        vote_count = Vote.query.filter_by(phase_id=phase.id).count()
        if vote_count > 0:
            return phase
    return None  # 找不到有票的已結束階段

# 🔹 關閉目前開啟階段
@admin_votes_bp.route('/phase/close', methods=['POST'], endpoint='close_phase')
def close_phase():
    current_phase = get_current_phase()
    if not current_phase:
        flash("⚠️ 無開啟中的階段", "warning")
        return redirect(url_for('admin_votes.admin_winners'))

    # ✅ 關閉階段（不要刪除票數）
    current_phase.is_open = False
    db.session.commit()

    flash(f"✅ 階段「{current_phase.name}」已成功關閉", "success")
    return redirect(url_for('admin_dashboard.admin_dashboard'))


# ✅ 開啟階段（僅允許一個）
@admin_votes_bp.route('/phase/open/<int:phase_id>', methods=['POST'], endpoint='open_phase')
def open_phase(phase_id):
    # 🔧 關閉所有階段
    VotePhase.query.update({VotePhase.is_open: False}, synchronize_session=False)

    # ✅ 開啟指定階段
    phase = VotePhase.query.get_or_404(phase_id)
    phase.is_open = True
    db.session.commit()

    flash(f"✅ 階段「{phase.name}」已成功開啟，其餘階段已關閉", "success")
    return redirect(url_for('admin_votes.admin_vote_phases'))

@admin_votes_bp.route('/vote_phases', endpoint='admin_vote_phases')
def admin_vote_phases():
    vote_title = get_setting("vote_title")
    phases = VotePhase.query.all()
    refresh_interval = get_setting("refresh_interval", 10)
    return render_template("admin_vote_phases.html",
                           vote_title=vote_title,
                           refresh_interval=refresh_interval,
                           phases=phases)  # ⬅️ 加這行！




@admin_votes_bp.route('/live_votes', methods=['GET'], endpoint='admin_live_votes')
def admin_live_votes():
    if 'admin_id' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    # 取得目前階段
    current_phase = get_current_phase()
    vote_title = Setting.query.filter_by(key='vote_title').first()
    
    # 從 Setting 取得 refresh_interval & slide_interval
    refresh_interval_setting = Setting.query.filter_by(key='refresh_interval').first()
    slide_interval_setting = Setting.query.filter_by(key='slide_interval').first()

    refresh_interval = int(refresh_interval_setting.value) if refresh_interval_setting else 10
    slide_interval = int(slide_interval_setting.value) if slide_interval_setting else 5  # 預設5秒

    # 沒有開啟中的階段就導去結果頁
    if not current_phase:
        flash("✅ 此階段投票已結束，請前往查看得票結果", "info")
        return redirect(url_for("admin_votes.admin_winners"))

    # 候選人
    candidates = Candidate.query.filter_by(phase_id=current_phase.id) \
        .order_by(Candidate.class_name, Candidate.name).all()

    # 計算得票數
    vote_counts = dict(
        db.session.query(
            Vote.candidate_id,
            func.count(Vote.id)
        ).filter_by(phase_id=current_phase.id)
         .group_by(Vote.candidate_id)
         .all()
    )

    # 年級分組
    grade_mapping = {
        '0': '幼兒園', '1': '一年級', '2': '二年級', '3': '三年級',
        '4': '四年級', '5': '五年級', '6': '六年級'
    }
    grade_order = ['幼兒園', '一年級', '二年級', '三年級', '四年級', '五年級', '六年級']

    grouped_candidates = {grade: [] for grade in grade_order}
    grouped_candidates_serializable = {grade: [] for grade in grade_order}

    for c in candidates:
        grade_key = str(c.class_name)[0] if c.class_name and c.class_name[:1].isdigit() else '0'
        grade = grade_mapping.get(grade_key, '幼兒園')
        if grade not in grade_order:
            continue
        grouped_candidates[grade].append(c)
        grouped_candidates_serializable[grade].append({
            'id': c.id,
            'class_display': c.class_name or '-',
            'parent_name': c.parent_name,
            'votes': vote_counts.get(c.id, 0)
        })

    # 排序
    for g in grade_order:
        grouped_candidates_serializable[g].sort(key=lambda x: (x['class_display'], x['parent_name']))

    # 全部
    all_candidates = []
    for g in grade_order:
        all_candidates.extend(grouped_candidates_serializable[g])

    grouped_with_all = OrderedDict()
    grouped_with_all['全部'] = all_candidates
    for g in grade_order:
        grouped_with_all[g] = grouped_candidates_serializable[g]

    # 分頁資訊
    grade_page_counts = {
        grade: (len(cands) // 30 + (1 if len(cands) % 30 > 0 else 0))
        for grade, cands in grouped_with_all.items()
    }

    return render_template(
        'admin_live_votes.html',
        candidates=candidates,
        current_phase=current_phase,
        vote_title=vote_title.value if vote_title else '',
        refresh_interval=refresh_interval,
        slide_interval=slide_interval,  # 🔥 補上
        vote_counts=vote_counts,
        grouped_candidates=grouped_candidates,
        grouped_candidates_serializable=grouped_with_all,
        grade_page_counts=grade_page_counts,
        is_closed=False
    )




# ✅ 投票階段管理頁面
@admin_votes_bp.route('/vote_phases', methods=['GET'], endpoint='manage_vote_phases')
def manage_vote_phases():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))
    vote_phases = VotePhase.query.all()
    return render_template('admin_vote_phases.html', vote_phases=vote_phases)

# ✅ 切換階段開關
@admin_votes_bp.route('/vote_phases/toggle/<int:phase_id>', methods=['POST'], endpoint='toggle_vote_phase')
def toggle_vote_phase(phase_id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    phase = VotePhase.query.get_or_404(phase_id)
    phase.is_open = not phase.is_open
    db.session.commit()
    flash(f"{phase.name} 階段已{'開啟' if phase.is_open else '關閉'}", 'success')
    return redirect(url_for('admin_votes.manage_vote_phases'))

# ✅ 關閉所有階段
@admin_votes_bp.route('/vote_phases/close_all', methods=['POST'], endpoint='close_all_phases')
def close_all_phases():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    VotePhase.query.update({VotePhase.is_open: False})
    db.session.commit()
    flash('✅ 已全部關閉所有投票階段', 'success')
    return redirect(url_for('admin_votes.manage_vote_phases'))

# ✅ 一鍵重設所有階段
@admin_votes_bp.route('/vote_phases/reset', methods=['POST'], endpoint='reset_vote_phases')
def reset_vote_phases():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    VotePhase.query.delete()
    db.session.commit()

    db.session.add_all([
        VotePhase(name='家長委員', max_votes=6, promote_count=41, is_open=True),
        VotePhase(name='常務委員', max_votes=3, promote_count=21, is_open=False),
        VotePhase(name='家長會長', max_votes=1, promote_count=1, is_open=False)
    ])
    db.session.commit()
    flash('✅ 已重設所有階段', 'success')
    return redirect(url_for('admin_votes.manage_vote_phases'))

# ✅ 清空票數
@admin_votes_bp.route('/votes/clear', methods=['POST'], endpoint='clear_parent_votes')
def clear_parent_votes():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    Vote.query.delete()
    db.session.commit()
    flash("✅ 所有家長會票數已清空", "success")
    return redirect(url_for('admin_votes.manage_vote_phases'))

# ✅ 得票結果頁（admin_winners.html）
from sqlalchemy import select

# ✅ 最新已結束階段投票結果
# admin_votes.py
@admin_votes_bp.route('/winners', methods=['GET'], endpoint='admin_winners')
def admin_winners():
    if 'admin_id' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    # ✅ 找出最新有票數的已結束階段
    phase_with_votes = (
        db.session.query(Vote.phase_id)
        .join(VotePhase, Vote.phase_id == VotePhase.id)
        .filter(VotePhase.is_open == False)
        .group_by(Vote.phase_id)
        .order_by(Vote.phase_id.desc())
        .first()
    )

    if not phase_with_votes:
        flash("⚠️ 尚無已結束的投票階段（或無任何票）", "warning")
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    phase_id = phase_with_votes[0]
    current_phase = VotePhase.query.get(phase_id)
    promote_count = current_phase.promote_count or 0

    # ✅ 查詢所有候選人與票數
    results = db.session.query(
        Candidate,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == current_phase.id)
    ).filter(
        Candidate.phase_id == current_phase.id
    ).group_by(Candidate.id).order_by(func.count(Vote.id).desc()).all()

    # ✅ 計算臨界票數
    if len(results) >= promote_count:
        threshold_vote = results[promote_count - 1][1]
    else:
        threshold_vote = 0

    # ✅ 判斷是否全部同票人可補滿名額
    count_above_threshold = len([r for r in results if r[1] > threshold_vote])
    same_as_threshold = [r for r in results if r[1] == threshold_vote]
    remaining_slots = promote_count - count_above_threshold

    candidates = []
    promoted_candidates = []

    for idx, (c, vote_count) in enumerate(results, start=1):
        c.rank = idx
        c.vote_count = vote_count

        if vote_count > threshold_vote:
            c.status = 'promoted'
            c.is_promoted = True
        elif vote_count == threshold_vote:
            if len(same_as_threshold) <= remaining_slots:
                c.status = 'promoted'  # ✅ 直接晉級
                c.is_promoted = True
            elif c.is_promoted:
                c.status = 'manual_promoted'  # 已勾選手動晉級
            else:
                c.status = 'tied'  # 同票但未處理
        else:
            c.status = 'not_promoted'

        if c.is_promoted:
            promoted_candidates.append(c)

        candidates.append(c)

    # ✅ 設定值
    vote_title = Setting.query.filter_by(key="vote_title").first()
    refresh_interval = Setting.query.filter_by(key="refresh_interval").first()

    return render_template("admin_winners.html",
                           candidates=candidates,
                           promoted_candidates=promoted_candidates,
                           current_phase=current_phase,
                           promote_count=promote_count,
                           vote_title=vote_title.value if vote_title else "投票結果",
                           refresh_interval=int(refresh_interval.value) if refresh_interval else 10)

# ✅ 手動選取同票候選人（admin_promote.html）
@admin_votes_bp.route('/promote', methods=['GET', 'POST'], endpoint='admin_tiebreaker')
def admin_tiebreaker():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    # ✅ 一開始強制清空快取
    db.session.expire_all()

    # ✅ 取得當前階段（先試開啟中，沒有就拿最新關閉的）
    current_phase = get_current_phase() or get_latest_phase()
    if not current_phase:
        flash('尚未建立任何投票階段', 'warning')
        return redirect(url_for('admin_votes.admin_winners'))

    promote_count = current_phase.promote_count or 1

    # ✅ 取得候選人與票數
    candidates = Candidate.query.filter_by(phase_id=current_phase.id).all()
    votes = db.session.query(
        Candidate.id,
        func.count(Vote.id)
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == current_phase.id)
    ).filter(
        Candidate.phase_id == current_phase.id
    ).group_by(Candidate.id).all()

    vote_counts = {cid: count for cid, count in votes}
    sorted_candidates = sorted(candidates, key=lambda c: vote_counts.get(c.id, 0), reverse=True)

    # ✅ 同票判斷邏輯（只有在晉級邊界外票數相同才算）
    threshold_vote = vote_counts.get(sorted_candidates[promote_count - 1].id, 0) if len(sorted_candidates) >= promote_count else 0
    tie_candidates = [
        c for idx, c in enumerate(sorted_candidates)
        if vote_counts.get(c.id, 0) == threshold_vote and idx >= promote_count
    ]
    need_manual = promote_count > 0 and len(tie_candidates) > 0

    # ✅ POST 處理（儲存手動選取者）
    if request.method == 'POST':
        selected_ids = request.form.getlist('selected_candidates')
        if not selected_ids:
            flash('請至少選擇一位候選人', 'danger')
            return redirect(url_for('admin_votes.admin_tiebreaker'))

        for c in candidates:
            c.is_winner = str(c.id) in selected_ids
        db.session.commit()
        flash('✅ 手動當選人已儲存成功', 'success')
        return redirect(url_for('admin_votes.admin_winners'))

    # ✅ 傳回頁面
    return render_template('admin_promote.html',
                           phase=current_phase,
                           promote_limit=promote_count,
                           tie_candidates=tie_candidates,
                           tiebreak_needed_count=len(tie_candidates),
                           need_manual=need_manual,
                           candidates=sorted_candidates,
                           promoted_candidates=[c for c in sorted_candidates if c.is_winner],
                           has_next_phase=VotePhase.query.filter(VotePhase.id > current_phase.id).first() is not None)

@admin_votes_bp.route('/api/live_votes', methods=['GET'])
def api_live_votes():
    # 1) 確認已登入管理員
    if 'admin_id' not in session:
        return jsonify({"error": "unauthorized"}), 403

    current_phase = get_current_phase()
    if not current_phase:
        return jsonify([])

    # 2) 只抓 id + 票數，效率較好
    results = (
        db.session.query(
            Candidate.id,
            func.count(Vote.id).label('vote_count')
        )
        .outerjoin(
            Vote,
            (Candidate.id == Vote.candidate_id) & (Vote.phase_id == current_phase.id)
        )
        .filter(Candidate.phase_id == current_phase.id)
        .group_by(Candidate.id)
        .all()
    )

    # 3) 回傳「純 list」——你的 updateVotes() 已支援
    return jsonify([
        {"id": cid, "vote_count": int(votes)}
        for cid, votes in results
    ])


@admin_votes_bp.route('/open_next_phase', methods=['POST'], endpoint='open_next_phase')
def open_next_phase():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    current_phase = get_latest_phase()
    next_phase = VotePhase.query.filter(VotePhase.id > current_phase.id).order_by(VotePhase.id).first()

    if not next_phase:
        flash("⚠️ 已無下一階段", "warning")
        return redirect(url_for('admin_votes.admin_winners'))

    next_phase.is_open = True
    db.session.commit()
    flash(f"✅ 已開啟下一階段：{next_phase.name}", "success")
    return redirect(url_for('admin_votes.admin_winners'))

@admin_votes_bp.route('/votes_log')
def votes_log():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    from sqlalchemy.orm import aliased
    Voter = aliased(Candidate)
    Target = aliased(Candidate)

    votes = (
        db.session.query(
            Vote.id,
            VotePhase.name.label("phase"),
            Voter.class_name.label("voter_class"),
            Voter.parent_name.label("voter_name"),
            Target.class_name.label("target_class"),
            Target.parent_name.label("target_name")
        )
        .join(VotePhase, Vote.phase_id == VotePhase.id)
        .join(Voter, Vote.voter_id == Voter.id)
        .join(Target, Vote.candidate_id == Target.id)
        .order_by(VotePhase.id, Vote.id)
        .all()
    )

    vote_details = [
        {
            "phase": v.phase,
            "voter": f"{v.voter_class} {v.voter_name}",
            "candidate": f"{v.target_class} {v.target_name}"
        }
        for v in votes
    ]
    return render_template('admin_votes_log.html', votes=vote_details)
