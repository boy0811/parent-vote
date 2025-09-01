# voting_system/admin/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Admin
from utils.helpers import add_log   # ✅ 記得匯入
from models import db, Admin


admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix="/admin")

# ✅ 管理員登入
@admin_auth_bp.route('/login', methods=['GET', 'POST'], endpoint='admin_login')
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            session['admin_id'] = admin.id
            session['admin'] = True  # 供其他檢查用
            add_log("admin", admin.id, "管理員登入")
            flash('✅ 歡迎回來！', 'success')
            return redirect(url_for('admin_dashboard.admin_dashboard'))

        # 登入失敗也記一下（user_id 可為 None）
        add_log("admin", None, f"管理員登入失敗（帳號：{username}）")
        flash('❌ 帳號或密碼錯誤', 'danger')

    return render_template('admin_login.html')

# ✅ 管理員登出
@admin_auth_bp.route('/logout', endpoint='admin_logout')
def admin_logout():
    admin_id = session.get('admin_id')  # 先取再清
    add_log("admin", admin_id, "管理員登出")

    # 你可以用 session.clear() 一次清掉，也可以個別 pop
    session.clear()
    flash('👋 已成功登出', 'info')
    return redirect(url_for('admin_auth.admin_login'))

@admin_auth_bp.route('/change_password', methods=['GET', 'POST'])
def change_password():
    # 確保已登入
    if 'admin_id' not in session:
        flash("請先登入管理員帳號", "warning")
        return redirect(url_for('admin_auth.admin_login'))

    admin = Admin.query.get(session['admin_id'])

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 檢查舊密碼
        if not admin.check_password(current_password):
            flash("目前密碼不正確", "danger")
            return render_template('admin_change_password.html')

        # 確認新密碼一致
        if new_password != confirm_password:
            flash("新密碼與確認密碼不一致", "danger")
            return render_template('admin_change_password.html')

        # 更新密碼
        admin.set_password(new_password)
        db.session.commit()
        flash("密碼已成功更新！", "success")
        return redirect(url_for('admin_dashboard.admin_dashboard'))

    return render_template('admin_change_password.html')
