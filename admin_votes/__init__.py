from flask import Blueprint, render_template, redirect, url_for, flash, send_file, request
from models import db, Candidate, Vote, VotePhase
from io import BytesIO
import pandas as pd

# ✅ 建立 Blueprint，並指定 url_prefix="/admin"
admin_votes = Blueprint("admin_votes", __name__, url_prefix="/admin")

# ✅ 即時監票
@admin_votes.route("/live_votes")
def admin_live_votes():
    candidates = Candidate.query.all()
    vote_counts = {
        c.id: Vote.query.filter_by(candidate_id=c.id).count()
        for c in candidates
    }
    current_phase = VotePhase.query.filter_by(is_active=True).first()
    return render_template("admin/admin_live_votes.html",
                           candidates=candidates,
                           vote_counts=vote_counts,
                           current_phase=current_phase)

# ✅ 得票排名頁
@admin_votes.route("/winners")
def admin_winners():
    candidates = Candidate.query.all()
    vote_counts = {
        c.id: Vote.query.filter_by(candidate_id=c.id).count()
        for c in candidates
    }
    sorted_candidates = sorted(candidates, key=lambda c: vote_counts.get(c.id, 0), reverse=True)
    return render_template("admin/admin_winners.html",
                           candidates=sorted_candidates,
                           vote_counts=vote_counts)

# ✅ 同票處理（手動選擇）
@admin_votes.route("/select_tiebreak")
def admin_select_tiebreak():
    return render_template("admin/admin_select_tiebreak.html")

# ✅ 投票階段開關
@admin_votes.route("/toggle_phase", methods=["GET", "POST"], endpoint="admin_toggle_phase")
def admin_toggle_phase():
    phases = VotePhase.query.all()
    if request.method == "POST":
        for phase in phases:
            phase_id = str(phase.id)
            is_active = request.form.get("phase_" + phase_id) == "on"
            phase.is_active = is_active
        db.session.commit()
        flash("✅ 投票階段設定已更新", "success")
        return redirect(url_for("admin_votes.admin_toggle_phase"))
    return render_template("admin/admin_toggle_phase.html", phases=phases)

# ✅ 匯出票數統計
@admin_votes.route("/export_vote_results")
def export_vote_results():
    votes = db.session.query(Vote).all()
    data = []
    for vote in votes:
        candidate = Candidate.query.get(vote.candidate_id)
        data.append({
            "候選人": candidate.name,
            "班級": candidate.class_name,
            "家長姓名": candidate.parent_name,
            "時間": vote.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="投票記錄")
    output.seek(0)
    return send_file(output, download_name="vote_results.xlsx", as_attachment=True)

# ✅ 清空所有家長會票數
@admin_votes.route("/reset_all_votes")
def reset_all_votes():
    db.session.query(Vote).delete()
    db.session.commit()
    flash("✅ 家長會所有票數已清空")
    return redirect(url_for("admin_votes.admin_live_votes"))
