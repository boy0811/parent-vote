from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Staff, StaffVote, Setting

admin_staffs_bp = Blueprint('admin_staffs', __name__)

# 名單列表
@admin_staffs_bp.route('/staff_list', methods=['GET'], endpoint='admin_staff_list')
def admin_staff_list():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staff_list = Staff.query.all()
    return render_template('admin_staff_list.html', staffs=staff_list)


# 新增
@admin_staffs_bp.route('/staff_add', methods=['GET', 'POST'], endpoint='admin_staff_add')
def admin_staff_add():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name = request.form.get('name', '').strip()
        class_name = request.form.get('class_name', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('⚠️ 帳號與密碼必填', 'danger')
            return redirect(url_for('admin_staffs.admin_staff_add'))

        if Staff.query.filter_by(username=username).first():
            flash('⚠️ 此帳號已存在', 'danger')
            return redirect(url_for('admin_staffs.admin_staff_add'))

        new_staff = Staff(username=username, name=name, class_name=class_name)
        new_staff.set_password(password)
        db.session.add(new_staff)
        db.session.commit()

        flash('✅ 教職員新增成功', 'success')
        return redirect(url_for('admin_staffs.admin_staff_list'))

    return render_template('admin_staff_form.html', staff=None)


# 編輯
@admin_staffs_bp.route('/staff_edit/<int:staff_id>', methods=['GET', 'POST'], endpoint='admin_staff_edit')
def admin_staff_edit(staff_id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staff = Staff.query.get_or_404(staff_id)

    if request.method == 'POST':
        staff.username = request.form.get('username', '').strip()
        staff.name = request.form.get('name', '').strip()
        staff.class_name = request.form.get('class_name', '').strip()
        password = request.form.get('password', '').strip()

        if password:
            staff.set_password(password)

        db.session.commit()
        flash('✅ 教職員資料已更新', 'success')
        return redirect(url_for('admin_staffs.admin_staff_list'))

    return render_template('admin_staff_form.html', staff=staff)


# 刪除
@admin_staffs_bp.route('/staff_delete/<int:staff_id>', methods=['POST'], endpoint='admin_staff_delete')
def admin_staff_delete(staff_id):
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    staff = Staff.query.get_or_404(staff_id)
    db.session.delete(staff)
    db.session.commit()

    flash('✅ 教職員已刪除', 'info')
    return redirect(url_for('admin_staffs.admin_staff_list'))

# 教職員投票標題設定
@admin_staffs_bp.route('/staff_vote_title', methods=['GET', 'POST'], endpoint='admin_staff_vote_title')
def admin_staff_vote_title():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    setting = Setting.query.filter_by(key='staff_vote_title').first()
    if not setting:
        setting = Setting(key='staff_vote_title', value='教職員投票')
        db.session.add(setting)
        db.session.commit()

    if request.method == 'POST':
        new_title = request.form.get('title', '').strip()
        setting.value = new_title
        db.session.commit()
        flash('✅ 教職員投票標題已更新', 'success')
        return redirect(url_for('admin_staffs.admin_staff_vote_title'))

    return render_template('admin_staff_vote_title.html', title=setting.value)

@admin_staffs_bp.route('/staff_votes/reset', methods=['POST'], endpoint='admin_reset_staff_votes')
def admin_reset_staff_votes():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    StaffVote.query.delete()
    db.session.commit()
    flash('✅ 教職員票數已清空', 'success')
    return redirect(url_for('admin_dashboard.admin_dashboard'))

# 匯入教職員名單
@admin_staffs_bp.route('/staff_import', methods=['GET', 'POST'], endpoint='admin_staff_import')
def admin_staff_import():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash("⚠️ 請選擇檔案", "danger")
            return redirect(url_for('admin_staffs.admin_staff_import'))

        # TODO: 這裡加上實際的匯入處理（例如讀 CSV/Excel）
        flash("✅ 教職員名單匯入成功", "success")
        return redirect(url_for('admin_staffs.admin_staff_list'))

    return render_template('admin_staff_import.html')


# 下載匯入範例
@admin_staffs_bp.route('/staff_template', methods=['GET'], endpoint='admin_staff_template')
def admin_staff_template():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    from flask import send_file
    import os

    template_path = os.path.join("static", "templates", "staff_template.xlsx")
    if not os.path.exists(template_path):
        flash("⚠️ 範例檔案不存在", "danger")
        return redirect(url_for('admin_staffs.admin_staff_list'))

    return send_file(template_path, as_attachment=True)
