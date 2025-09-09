from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models import db, Candidate, VotePhase, Vote
import pandas as pd
import csv
from sqlalchemy import func

admin_candidates_bp = Blueprint('admin_candidates', __name__, url_prefix='/admin')


# ✅ 匯入候選人
@admin_candidates_bp.route('/candidates/import', methods=['GET', 'POST'], endpoint='admin_import_candidates')
def import_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('請選擇檔案', 'danger')
            return redirect(url_for('admin_candidates.admin_import_candidates'))

        ext = file.filename.lower().split('.')[-1]

        try:
            # CSV
            if ext == "csv":
                try:
                    file.stream.seek(0)
                    reader = csv.DictReader((line.decode("utf-8-sig") for line in file.stream))
                except UnicodeDecodeError:
                    file.stream.seek(0)
                    reader = csv.DictReader((line.decode("big5") for line in file.stream))
                rows = list(reader)

            # Excel
            else:
                df = pd.read_excel(file, dtype=str, engine="openpyxl").fillna("")
                rows = df.to_dict(orient="records")

        except Exception as e:
            flash(f'❌ 讀取檔案失敗：{e}', 'danger')
            return redirect(url_for('admin_candidates.admin_import_candidates'))

        # 檢查必填欄位
        required_cols = {'帳號', '密碼', '班級', '家長姓名'}
        if not rows or not required_cols.issubset(rows[0].keys()):
            flash(f'❌ 匯入失敗：缺少必要欄位 {required_cols}', 'danger')
            return redirect(url_for('admin_candidates.admin_import_candidates'))

        # 取得第一階段 id
        first_phase_id = db.session.query(func.min(VotePhase.id)).scalar()
        if not first_phase_id:
            flash('❌ 尚未建立任何投票階段，請先建立。', 'danger')
            return redirect(url_for('admin_candidates.admin_import_candidates'))

        created, updated, skipped = 0, 0, 0

        try:
            for row in rows:
                username = (row.get('帳號') or '').strip()
                password = str(row.get('密碼') or '').strip() or '1234'
                class_name = (row.get('班級') or '').strip()
                parent_name = (row.get('家長姓名') or '').strip()

                if not username:
                    skipped += 1
                    continue

                cand = db.session.query(Candidate).filter_by(
                    username=username, phase_id=first_phase_id
                ).first()

                if cand:
                    # 更新
                    cand.name = parent_name
                    cand.parent_name = parent_name
                    cand.class_name = class_name
                    cand.set_password(password)
                    updated += 1
                else:
                    # 新增
                    cand = Candidate(
                        username=username,
                        name=parent_name,
                        parent_name=parent_name,
                        class_name=class_name,
                        phase_id=first_phase_id
                    )
                    cand.set_password(password)
                    db.session.add(cand)
                    created += 1

            db.session.commit()
            flash(f'✅ 匯入完成：新增 {created} 筆、更新 {updated} 筆、略過 {skipped} 筆', 'success')

        except Exception as e:
            db.session.rollback()
            flash(f'❌ 匯入失敗並已回滾：{e}', 'danger')

        return redirect(url_for('admin_candidates.admin_import_candidates'))

    return render_template('admin_import_candidates.html')


# ✅ 候選人列表
@admin_candidates_bp.route('/candidates', methods=['GET'], endpoint='admin_candidate_list')
def admin_candidate_list():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    candidates = Candidate.query.all()
    return render_template('admin_candidates.html', candidates=candidates)


# ✅ 新增候選人
@admin_candidates_bp.route('/candidates/add', methods=['GET', 'POST'], endpoint='admin_add_candidate')
def admin_add_candidate():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        candidate = Candidate(
            username=request.form['username'],
            name=request.form['parent_name'],
            parent_name=request.form['parent_name'],
            class_name=request.form['class_name']
        )
        candidate.set_password(request.form['password'])
        db.session.add(candidate)
        db.session.commit()
        flash('✅ 新增成功', 'success')
        return redirect(url_for('admin_candidates.admin_candidate_list'))

    return render_template('admin_candidate_form.html', candidate=None)


# ✅ 編輯候選人
@admin_candidates_bp.route('/candidates/edit/<int:candidate_id>', methods=['GET', 'POST'], endpoint='admin_edit_candidate')
def admin_edit_candidate(candidate_id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    candidate = Candidate.query.get_or_404(candidate_id)

    if request.method == 'POST':
        candidate.username = request.form['username']
        candidate.name = request.form['parent_name']
        candidate.parent_name = request.form['parent_name']
        candidate.class_name = request.form['class_name']
        if request.form['password']:
            candidate.set_password(request.form['password'])
        db.session.commit()
        flash('✅ 修改成功', 'success')
        return redirect(url_for('admin_candidates.admin_candidate_list'))

    return render_template('admin_candidate_form.html', candidate=candidate)


# ✅ 刪除單一候選人
@admin_candidates_bp.route('/candidates/delete/<int:candidate_id>', methods=['GET'], endpoint='admin_delete_candidate')
def admin_delete_candidate(candidate_id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    candidate = Candidate.query.get_or_404(candidate_id)
    Vote.query.filter(Vote.candidate_id == candidate_id).delete(synchronize_session=False)
    db.session.delete(candidate)
    db.session.commit()
    flash('✅ 刪除成功', 'info')
    return redirect(url_for('admin_candidates.admin_candidate_list'))


# ✅ 批次刪除候選人
@admin_candidates_bp.route('/candidates/delete', methods=['POST'], endpoint='admin_delete_candidates')
def admin_delete_candidates():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    ids = request.form.getlist('candidate_ids')
    if ids:
        try:
            ids = [int(i) for i in ids]
            Vote.query.filter(Vote.candidate_id.in_(ids)).delete(synchronize_session=False)
            Candidate.query.filter(Candidate.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            flash(f'✅ 已成功刪除 {len(ids)} 位候選人及其票數', 'success')
        except ValueError:
            flash('❌ 候選人 ID 格式錯誤', 'danger')
            db.session.rollback()
    else:
        flash('⚠️ 請選擇要刪除的候選人', 'warning')

    return redirect(url_for('admin_candidates.admin_candidate_list'))
