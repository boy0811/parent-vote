from flask import Blueprint, render_template, redirect, url_for, request, session, flash, send_file
from models import db, Candidate, VotePhase, Vote
from datetime import datetime
import pandas as pd
from io import BytesIO

admin_candidates_bp = Blueprint('admin_candidates', __name__)

# 匯出候選人（xlsx）
@admin_candidates_bp.route('/admin/candidates/export', endpoint='admin_export_candidates')
def export_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    candidates = Candidate.query.all()
    data = [{
        '帳號': c.username,
        '班級': c.class_name or '',
        '家長姓名': c.parent_name or '',
        '學生姓名': c.name or '',
        '所屬階段': c.phase_id
    } for c in candidates]
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='候選人名單.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 候選人名單頁
@admin_candidates_bp.route('/admin/candidates', endpoint='admin_candidates')
def admin_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))
    phases = VotePhase.query.order_by(VotePhase.id).all()
    candidates_by_phase = {
        phase.id: Candidate.query.filter_by(phase_id=phase.id).all()
        for phase in phases
    }
    return render_template('admin_candidates.html', phases=phases, candidates_by_phase=candidates_by_phase)

# 新增候選人
@admin_candidates_bp.route('/admin/candidates/add', methods=['GET', 'POST'], endpoint='admin_add_candidate')
def admin_add_candidate():
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    phases = VotePhase.query.all()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        phase_id = request.form.get('phase_id')
        class_name = request.form.get('class_name')
        parent_name = request.form.get('parent_name')

        if username and password and phase_id:
            c = Candidate(username=username, name=name, phase_id=int(phase_id), class_name=class_name, parent_name=parent_name)
            c.set_password(password)
            db.session.add(c)
            db.session.commit()
            flash('新增成功', 'success')
            return redirect(url_for('admin_candidates.admin_candidates'))
        else:
            flash('請填寫完整資料', 'danger')

    return render_template('admin_edit_candidate.html', candidate=None, phases=phases)

# 編輯候選人
@admin_candidates_bp.route('/admin/candidates/edit/<int:id>', methods=['GET', 'POST'], endpoint='admin_edit_candidate')
def admin_edit_candidate(id):
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    c = Candidate.query.get_or_404(id)
    phases = VotePhase.query.all()

    if request.method == 'POST':
        c.username = request.form.get('username')
        password = request.form.get('password')
        c.name = request.form.get('name')
        c.class_name = request.form.get('class_name')
        c.parent_name = request.form.get('parent_name')
        c.phase_id = int(request.form.get('phase_id'))
        if password.strip():
            c.set_password(password)
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('admin_candidates.admin_candidates'))

    return render_template('admin_edit_candidate.html', candidate=c, phases=phases)

# 刪除候選人
@admin_candidates_bp.route('/admin/candidates/delete/<int:id>', methods=['POST'], endpoint='admin_delete_candidate')
def admin_delete_candidate(id):
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    c = Candidate.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash('刪除成功', 'info')
    return redirect(url_for('admin_candidates.admin_candidates'))

# 匯入候選人
@admin_candidates_bp.route('/admin/candidates/import', methods=['GET', 'POST'], endpoint='admin_import_candidates')
def import_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            for _, row in df.iterrows():
                if pd.isna(row.get('帳號')) or pd.isna(row.get('密碼')):
                    continue
                c = Candidate(
                    username=str(row.get('帳號')),
                    class_name=str(row.get('班級')) if not pd.isna(row.get('班級')) else None,
                    parent_name=str(row.get('家長姓名')) if not pd.isna(row.get('家長姓名')) else None,
                    name=str(row.get('學生姓名')) if not pd.isna(row.get('學生姓名')) else None,
                    phase_id=int(row.get('所屬階段')) if not pd.isna(row.get('所屬階段')) else 1
                )
                c.set_password(str(row.get('密碼')))
                db.session.add(c)
            db.session.commit()
            flash('匯入成功', 'success')
            return redirect(url_for('admin_candidates.admin_candidates'))
        else:
            flash('請上傳 .xlsx 檔案', 'danger')

    return render_template('admin_candidate_import.html')

# 批次晉級
@admin_candidates_bp.route('/admin/promote/<int:phase_id>', methods=['GET', 'POST'], endpoint='admin_promote_candidates')
def admin_promote_candidates(phase_id):
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    current_phase = VotePhase.query.get_or_404(phase_id)
    next_phase = VotePhase.query.filter(VotePhase.id > phase_id).order_by(VotePhase.id).first()

    if not next_phase:
        flash('已無下一階段', 'warning')
        return redirect(url_for('admin_candidates.admin_candidates'))

    if request.method == 'POST':
        selected_ids = request.form.getlist('selected_ids')
        for cid in selected_ids:
            candidate = Candidate.query.get(int(cid))
            if candidate and candidate.phase_id == phase_id:
                candidate.phase_id = next_phase.id
        db.session.commit()
        flash('已成功晉級', 'success')
        return redirect(url_for('admin_candidates.admin_candidates'))

    candidates = Candidate.query.filter_by(phase_id=phase_id).order_by(Candidate.vote_count.desc()).all()
    return render_template('admin_promote.html', candidates=candidates, current_phase=current_phase)

# 單一降級
@admin_candidates_bp.route('/admin/demote_one/<int:id>', endpoint='demote_one')
def demote_one(id):
    if 'admin' not in session:
        return redirect(url_for('admin.admin_login'))

    c = Candidate.query.get_or_404(id)
    previous_phase = VotePhase.query.filter(VotePhase.id < c.phase_id).order_by(VotePhase.id.desc()).first()

    if previous_phase:
        c.phase_id = previous_phase.id
        db.session.commit()
        flash('已成功降級', 'info')
    else:
        flash('已是最低階段', 'warning')

    return redirect(url_for('admin_candidates.admin_candidates'))
