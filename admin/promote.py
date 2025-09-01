from flask import Blueprint, render_template, redirect, url_for, flash, request, send_file
from models import db, VotePhase, Candidate, Vote
from sqlalchemy import func
import io
import pandas as pd

admin_promote_bp = Blueprint('admin_promote', __name__, url_prefix="/admin")


# ✅ 取得最新結束階段
def get_latest_closed_phase():
    return VotePhase.query.filter_by(is_open=False).order_by(VotePhase.id.desc()).first()

# ✅ 安全取得下一階段
def get_next_phase(current_phase_id):
    return VotePhase.query.filter(VotePhase.id > current_phase_id).order_by(VotePhase.id.asc()).first()


# ✅ 取得票數與名次資料
def get_vote_results_with_rank(phase_id):
    results = db.session.query(
        Candidate,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == phase_id)
    ).filter(
        Candidate.phase_id == phase_id
    ).group_by(Candidate.id).order_by(func.count(Vote.id).desc()).all()

    ranked_results = []
    rank = 0
    prev_vote = None
    for idx, (candidate, vote_count) in enumerate(results, start=1):
        if vote_count != prev_vote:
            rank = idx
            prev_vote = vote_count
        ranked_results.append((candidate, vote_count, rank))
    return ranked_results


# ✅ 顯示晉級處理頁面
@admin_promote_bp.route('/promote', methods=['GET'], endpoint='promote_page')
def promote_page():
    phase_id = request.args.get('phase_id', type=int)
    current_phase = VotePhase.query.get(phase_id) if phase_id else get_latest_closed_phase()

    if not current_phase:
        flash("⚠️ 尚無可供檢視的階段", "warning")
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    promote_count = current_phase.promote_count or 0

    # 取得票數資料（排序 + 計票）
    results = db.session.query(
        Candidate,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == current_phase.id)
    ).filter(
        Candidate.phase_id == current_phase.id
    ).group_by(Candidate.id).order_by(func.count(Vote.id).desc()).all()

    # 自動晉級與同票候選人計算
    if len(results) < promote_count:
        auto_promoted = results
        tied_candidates = []
        remaining_to_promote = 0
    else:
        cutoff_vote = results[promote_count - 1][1]
        all_with_cutoff = [(c, v) for c, v in results if v == cutoff_vote]
        before_cutoff = [(c, v) for c, v in results if v > cutoff_vote]

        if len(before_cutoff) + len(all_with_cutoff) <= promote_count:
            auto_promoted = before_cutoff + all_with_cutoff
            tied_candidates = []
            remaining_to_promote = 0
        else:
            auto_promoted = before_cutoff
            tied_candidates = all_with_cutoff
            remaining_to_promote = promote_count - len(before_cutoff)

    # ✅ 僅設定 auto_promoted，不清空整個階段狀態，避免蓋掉 manual 勾選者
    for c, _ in auto_promoted:
        candidate = Candidate.query.get(c.id)
        if candidate:
            candidate.is_promoted = True
            candidate.promote_type = 'auto'

    db.session.commit()

    # ✅ 統計目前已晉級人數
    actual_promoted_count = Candidate.query.filter_by(
        phase_id=current_phase.id, is_promoted=True
    ).count()

    # 取得所有階段（供選單用）
    phases = VotePhase.query.order_by(VotePhase.id).all()

    return render_template('admin_promote.html',
                          current_phase=current_phase,
                          promote_count=promote_count,
                          auto_promoted=auto_promoted,
                          tied_candidates=tied_candidates,
                          remaining_to_promote=remaining_to_promote,
                          actual_promoted_count=actual_promoted_count,
                          phases=phases)



# ✅ 儲存手動選取者
# ✅ 完整修正 save_promoted_candidates()
@admin_promote_bp.route('/promote/save', methods=['POST'], endpoint='save_promoted_candidates')
def save_promoted_candidates():
    phase_id = int(request.form.get('phase_id'))
    selected_ids = request.form.getlist('candidate_ids')  # 同票者手動勾選的 ID（字串）
    selected_ids = [int(x) for x in selected_ids]

    phase = VotePhase.query.get(phase_id)
    if not phase:
        flash("❌ 找不到此階段", "danger")
        return redirect(url_for('admin_promote.promote_page'))

    promote_count = phase.promote_count or 0

    # 1) 取得此階段所有候選人票數（由高到低）
    results = db.session.query(
        Candidate,
        func.count(Vote.id).label('vote_count')
    ).outerjoin(
        Vote, (Vote.candidate_id == Candidate.id) & (Vote.phase_id == phase_id)
    ).filter(
        Candidate.phase_id == phase_id
    ).group_by(Candidate.id).order_by(func.count(Vote.id).desc()).all()

    if not results:
        flash("⚠️ 找不到任何候選人", "warning")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase_id))

    # 2) 找 cutoff（第 promote_count 名的票數）
    cutoff_vote = 0 if len(results) < promote_count else results[promote_count - 1][1]

    auto_promoted = [c for c, v in results if v > cutoff_vote]
    tied_candidates = [c for c, v in results if v == cutoff_vote]

    auto_ids = [c.id for c in auto_promoted]

    # 3) 剛好補滿就全自動；否則檢查手動勾選數是否正確
    if len(auto_ids) + len(tied_candidates) == promote_count:
        manual_ids = []
        auto_ids.extend([c.id for c in tied_candidates])
    else:
        manual_ids = selected_ids
        if len(auto_ids) + len(manual_ids) != promote_count:
            flash(f"⚠️ 請勾選正確人數，共需 {promote_count} 人，已勾選 {len(manual_ids)} 人", "danger")
            return redirect(url_for('admin_promote.promote_page', phase_id=phase_id))

    final_promoted_ids = set(auto_ids + manual_ids)

    # 4) 更新本階段候選人晉級狀態
    for c in Candidate.query.filter_by(phase_id=phase_id).all():
        if c.id in final_promoted_ids:
            c.is_promoted = True
            c.promote_type = 'auto' if c.id in auto_ids else 'manual'
        else:
            c.is_promoted = False
            c.promote_type = None

    try:
        db.session.flush()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("❌ 資料庫儲存失敗", "danger")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase_id))

    # 5) 建立下一階段候選人（若有）
    next_phase = get_next_phase(phase_id)  # 你上面已經有這個 helper
    if not next_phase:
        flash("🎉 已是最後階段，晉級名單已儲存。", "success")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase_id))

    promoted_candidates = Candidate.query.filter_by(phase_id=phase_id, is_promoted=True).all()

    added_count = 0
    for c in promoted_candidates:
        exists = Candidate.query.filter_by(username=c.username.strip(), phase_id=next_phase.id).first()
        if exists:
            continue
        db.session.add(Candidate(
            username=c.username,
            password_hash=c.password_hash,
            name=c.name,
            class_name=c.class_name,
            parent_name=c.parent_name,
            phase_id=next_phase.id,
            is_signed_in=False,
            is_promoted=False,
            is_winner=False,
            promote_type=None,
            has_voted=False
        ))
        added_count += 1

    db.session.commit()

    flash(f"✅ 晉級名單已儲存，並已建立 {added_count} 位至下一階段「{next_phase.name}」。", "success")
    # 這裡會讓 1 -> 2、2 -> 3，依序跳
    return redirect(url_for('admin_promote.promote_page', phase_id=next_phase.id))

# ✅ 匯出投票結果（含名次）
@admin_promote_bp.route('/export_vote_results', methods=['GET'], endpoint='export_vote_results')
def export_vote_results():
    import io
    import pandas as pd
    from flask import send_file

    # ---- 0) 參數檢查 ----
    phase_id = request.args.get('phase_id', type=int)
    if not phase_id:
        flash("⚠️ 請指定要匯出的階段 (phase_id)", "warning")
        return redirect(url_for('admin_promote.promote_page'))

    phase = VotePhase.query.get(phase_id)
    if not phase:
        flash("⚠️ 找不到指定階段", "warning")
        return redirect(url_for('admin_promote.promote_page'))

    # ---- 1) 先把此階段的候選人抓出來 ----
    phase_candidates = Candidate.query.filter_by(phase_id=phase.id).order_by(Candidate.id.asc()).all()

    # ---- 1.1) 檢查是否有候選人 phase_id 不等於當前階段 ----
    wrong_phase_candidates = [c for c in phase_candidates if c.phase_id != phase.id]
    if wrong_phase_candidates:
        flash("⚠️ 這個階段的候選人資料中含有錯誤的 phase_id，請先修正資料。", "danger")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase.id))

    # ---- 2) 查詢此階段候選人的投票數 ----
    results = (
        db.session.query(
            Candidate,
            func.count(Vote.id).label('vote_count')
        )
        .outerjoin(
            Vote,
            (Vote.candidate_id == Candidate.id) & (Vote.phase_id == phase.id)
        )
        .filter(Candidate.phase_id == phase.id)
        .group_by(Candidate.id)
        .order_by(func.count(Vote.id).desc(), Candidate.id.asc())
        .all()
    )

    if not results:
        flash("⚠️ 此階段無投票資料", "warning")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase.id))

    # ---- 3) 額外偵測：是否有跨階段的 Vote 記錄 ----
    cand_ids = [c.id for c, _ in results]
    stray_votes = (
        db.session.query(Vote.phase_id, func.count(Vote.id))
        .filter(Vote.candidate_id.in_(cand_ids))
        .group_by(Vote.phase_id)
        .all()
    )
    exotic = [(pid, cnt) for pid, cnt in stray_votes if pid != phase.id]
    if exotic:
        flash("⚠️ 偵測到候選人的票數存在跨階段的紀錄（資料異常），請檢查資料庫。", "danger")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase.id))

    # ---- 4) 計算名次 ----
    data = []
    rank = 0
    prev_votes = None
    for idx, (c, votes) in enumerate(results, start=1):
        if votes != prev_votes:
            rank = idx
            prev_votes = votes
        data.append((rank, c.class_name, c.parent_name, int(votes)))

    # ---- 5) 匯出 Excel ----
    df = pd.DataFrame(data, columns=["名次", "班級", "家長姓名", "得票數"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        safe_sheet = f"{phase.name}投票結果"[:31]
        df.to_excel(writer, index=False, sheet_name=safe_sheet)
    output.seek(0)

    return send_file(
        output,
        download_name=f"投票結果_{phase.name}_ID{phase.id}.xlsx",
        as_attachment=True
    )

# ✅ 匯出晉級名單（含晉級方式）
@admin_promote_bp.route('/export_promoted_candidates', endpoint='export_promoted_candidates')
def export_promoted_candidates():
    import io
    import pandas as pd
    from flask import send_file

    phase_id = request.args.get('phase_id', type=int)
    if phase_id:
        phase = VotePhase.query.get(phase_id)
    else:
        phase = VotePhase.query.filter_by(is_open=False).order_by(VotePhase.id.desc()).first()

    if not phase:
        flash("⚠️ 找不到已結束的階段", "danger")
        return redirect(url_for('admin_promote.promote_page'))

    candidates = Candidate.query.filter_by(phase_id=phase.id, is_promoted=True).order_by(Candidate.id).all()
    if not candidates:
        flash("⚠️ 該階段尚無晉級名單", "warning")
        return redirect(url_for('admin_promote.promote_page', phase_id=phase.id))

    data = [(c.id, c.class_name, c.parent_name, c.promote_type or "auto") for c in candidates]
    df = pd.DataFrame(data, columns=["ID", "班級", "家長姓名", "晉級方式"])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='當選名單')
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'當選名單_{phase.name}_ID{phase.id}.xlsx'
    )


# ✅ 開啟下一階段
@admin_promote_bp.route('/open_next_phase', methods=['GET', 'POST'], endpoint='open_next_phase')
def open_next_phase():
    # 🔍 找出目前開啟的階段
    current_phase = VotePhase.query.filter_by(is_open=True).order_by(VotePhase.id).first()

    if not current_phase:
        flash("⚠️ 沒有開啟中的階段", "warning")
        return redirect(url_for('admin_promote.promote_page'))

    # 🔐 關閉目前階段
    current_phase.is_open = False
    db.session.commit()

    # ⏭️ 找下一個階段
    next_phase = VotePhase.query.filter(VotePhase.id > current_phase.id).order_by(VotePhase.id).first()

    if not next_phase:
        flash("⚠️ 沒有下一階段可啟用", "warning")
        return redirect(url_for('admin_promote.promote_page', phase_id=current_phase.id))

    # ✅ 開啟下一階段
    next_phase.is_open = True
    db.session.commit()

    flash(f"✅ 已關閉「{current_phase.name}」，並開啟下一階段：「{next_phase.name}」", "success")
    return redirect(url_for('admin_promote.promote_page', phase_id=next_phase.id))

# ✅ 查看所有晉級者列表
@admin_promote_bp.route("/promote/list", endpoint="promoted_list")
def promoted_list():
    candidates = Candidate.query.filter_by(is_promoted=True).order_by(Candidate.phase_id, Candidate.id).all()
    return render_template("promoted_list.html", candidates=candidates)


# ✅ 匯出所有晉級者名單
@admin_promote_bp.route("/promote/export_all", endpoint="export_all_promoted_candidates")
def export_all_promoted_candidates():
    import pandas as pd
    from io import BytesIO

    candidates = Candidate.query.filter_by(is_promoted=True).order_by(Candidate.phase_id, Candidate.id).all()
    data = [(c.phase_id, c.class_name, c.parent_name, c.promote_type or "") for c in candidates]

    df = pd.DataFrame(data, columns=["階段ID", "班級", "家長姓名", "晉級方式"])

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="所有晉級者")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name="所有晉級者名單.xlsx",
        as_attachment=True
    )

# ✅ 開啟本階段投票
@admin_promote_bp.route('/promote/open_phase/<int:phase_id>', methods=['POST'], endpoint='open_phase')
def open_phase(phase_id):
    # ✅ 先關閉所有階段
    VotePhase.query.update({VotePhase.is_open: False})
    db.session.commit()

    # ✅ 再開啟指定階段
    phase = VotePhase.query.get(phase_id)
    if not phase:
        flash("❌ 找不到指定階段", "danger")
        return redirect(url_for('admin_promote.promote_page'))

    phase.is_open = True
    db.session.commit()

    flash(f"✅ 已開啟階段「{phase.name}」，其他階段已關閉", "success")
    return redirect(url_for('admin_promote.promote_page', phase_id=phase_id))

# 👉 只負責「頁面跳下一階段」，不做任何資料異動
@admin_promote_bp.route('/promote/next', methods=['GET'], endpoint='goto_next_phase')
def goto_next_phase():
    # 目前所在階段（從 querystring 來）
    current_phase_id = request.args.get('phase_id', type=int)

    # 若沒帶，抓 promote_page 頁會用到的邏輯，也可直接抓第一個或最新結束階段
    if not current_phase_id:
        current_phase = get_latest_closed_phase() or VotePhase.query.order_by(VotePhase.id.asc()).first()
        if not current_phase:
            flash("⚠️ 尚無任何階段可切換", "warning")
            return redirect(url_for('admin_dashboard.admin_dashboard'))
        current_phase_id = current_phase.id

    # 找下一階段
    next_phase = get_next_phase(current_phase_id)
    if not next_phase:
        flash("🎉 已是最後階段，無法再轉跳。", "info")
        return redirect(url_for('admin_promote.promote_page', phase_id=current_phase_id))

    flash(f"➡️ 已切換至下一階段「{next_phase.name}」", "success")
    return redirect(url_for('admin_promote.promote_page', phase_id=next_phase.id))
