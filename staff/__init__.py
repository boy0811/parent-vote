from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from models import db, Staff, StaffVote, Setting
import pandas as pd
from io import BytesIO

staff_bp = Blueprint('staff', __name__)

# ----------------------
# 教職員登入
# ----------------------
@staff_bp.route('/login', methods=['GET', 'POST'], endpoint='staff_login')
def staff_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        staff = Staff.query.filter_by(username=username).first()
        if staff and staff.check_password(password):
            session['staff_id'] = staff.id
            session['staff_name'] = staff.name
            # ✅ 登入後直接到簽到面板
            return redirect(url_for('checkin_panel.panel'))
        else:
            flash('帳號或密碼錯誤', 'danger')

    return render_template('staff_login.html')

# ----------------------
# 教職員確認資料
# ----------------------
@staff_bp.route('/confirm', methods=['GET', 'POST'], endpoint='staff_confirm')
def staff_confirm():
    if 'staff_id' not in session:
        return redirect(url_for('staff.staff_login'))

    staff = Staff.query.get(session['staff_id'])

    if request.method == 'POST':
        staff.name = request.form['name']
        db.session.commit()
        return redirect(url_for('staff.staff_vote'))

    return render_template('staff_confirm.html', staff=staff)

# ----------------------
# 教職員投票
# ----------------------
@staff_bp.route('/vote', methods=['GET', 'POST'], endpoint='staff_vote')
def staff_vote():
    if 'staff_id' not in session:
        return redirect(url_for('staff.staff_login'))

    staff = Staff.query.get(session['staff_id'])

    # 取得投票標題
    vote_title_setting = Setting.query.filter_by(key='staff_vote_title').first()
    vote_title = vote_title_setting.value if vote_title_setting else '教職員意見調查'

    # 取得 current_reset_id（沒有的話用 '1'）
    current_reset_id = int(get_setting('current_reset_id', '1'))

    # 查詢是否已投票
    existing_vote = StaffVote.query.filter_by(staff_id=staff.id, reset_id=current_reset_id).first()

    if request.method == 'POST' and not existing_vote:
        choice = request.form.get('choice')  # 贊成 or 反對

        if choice in ['贊成', '反對']:
            vote = StaffVote(
                staff_id=staff.id,
                vote_result=choice,
                reset_id=current_reset_id
            )
            db.session.add(vote)
            db.session.commit()
            flash('投票成功', 'success')
            return redirect(url_for('staff.staff_vote'))
        else:
            flash('請選擇有效的投票選項', 'danger')

    # 票數統計
    agree_count = StaffVote.query.filter_by(vote_result='贊成', reset_id=current_reset_id).count()
    disagree_count = StaffVote.query.filter_by(vote_result='反對', reset_id=current_reset_id).count()

    return render_template(
        'staff_vote.html',
        staff=staff,
        existing_vote=existing_vote,
        agree_count=agree_count,
        disagree_count=disagree_count,
        vote_title=vote_title
    )

# ----------------------
# 教職員名單管理
# ----------------------
@staff_bp.route('/admin/staffs')
def admin_staffs():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))
    staffs = Staff.query.all()
    return render_template('admin_staffs.html', staffs=staffs)

@staff_bp.route('/admin/staffs/add', methods=['GET', 'POST'])
def admin_add_staff():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        class_name = request.form.get('class_name', '')

        if username and password:
            staff = Staff(username=username, name=name, class_name=class_name)
            staff.set_password(password)
            db.session.add(staff)
            db.session.commit()
            flash('新增成功', 'success')
            return redirect(url_for('staff.admin_staffs'))
        else:
            flash('請填寫帳號與密碼', 'danger')
    return render_template('admin_edit_staff.html', staff=None)

@staff_bp.route('/admin/staffs/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_staff(id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staff = Staff.query.get_or_404(id)
    if request.method == 'POST':
        staff.username = request.form.get('username')
        password = request.form.get('password')
        staff.name = request.form.get('name')
        staff.class_name = request.form.get('class_name', '')
        if password.strip():
            staff.set_password(password)
        db.session.commit()
        flash('修改成功', 'success')
        return redirect(url_for('staff.admin_staffs'))
    return render_template('admin_edit_staff.html', staff=staff)

@staff_bp.route('/admin/staffs/delete/<int:id>', methods=['POST'])
def admin_delete_staff(id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staff = Staff.query.get_or_404(id)
    db.session.delete(staff)
    db.session.commit()
    flash('刪除成功', 'info')
    return redirect(url_for('staff.admin_staffs'))

# ----------------------
# 匯出 & 匯入 & 範例下載
# ----------------------
@staff_bp.route('/admin/staffs/export')
def export_staffs():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staffs = Staff.query.all()
    data = [{
        '帳號': s.username,
        '姓名': s.name or '',
        '班級': s.class_name or ''
    } for s in staffs]
    df = pd.DataFrame(data)
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='教職員名單.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

@staff_bp.route('/admin/staffs/import', methods=['GET', 'POST'])
def import_staffs():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.xlsx'):
            df = pd.read_excel(file)
            created, updated, skipped = 0, 0, 0

            for _, row in df.iterrows():
                username = str(row.get('帳號') or '').strip()
                password = str(row.get('密碼') or '').strip()
                name = None if pd.isna(row.get('姓名')) else str(row.get('姓名')).strip()
                class_name = None if pd.isna(row.get('班級')) else str(row.get('班級')).strip()

                if not username or not password:
                    skipped += 1
                    continue

                existing = Staff.query.filter_by(username=username).first()
                if existing:
                    existing.name = name
                    existing.class_name = class_name
                    existing.set_password(password)
                    updated += 1
                else:
                    s = Staff(username=username, name=name, class_name=class_name)
                    s.set_password(password)
                    db.session.add(s)
                    created += 1

            db.session.commit()
            flash(f'✅ 匯入完成：新增 {created} 筆、更新 {updated} 筆、略過 {skipped} 筆', 'success')
            return redirect(url_for('staff.admin_staffs'))
        else:
            flash('請上傳 .xlsx 檔案', 'danger')
    return render_template('admin_staff_import.html')

@staff_bp.route('/admin/staffs/download_sample')
def download_sample_staffs():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))
    sample_data = pd.DataFrame([
        {'帳號': 'staff01', '密碼': '1234', '姓名': '王小明', '班級': '六年級'},
        {'帳號': 'staff02', '密碼': '5678', '姓名': '李小華', '班級': '五年級'},
    ])
    output = BytesIO()
    sample_data.to_excel(output, index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='教職員名單範例.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ----------------------
# 工具函式
# ----------------------
def get_setting(key, default=''):
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default
