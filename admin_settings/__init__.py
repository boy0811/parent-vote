from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Setting, VotePhase, StaffVote

admin_settings_bp = Blueprint('admin_settings', __name__)

# ✅ 工具函式：取得設定值
def get_setting(key):
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else ''

# ✅ 路由：顯示與更新系統設定頁（刷新秒數、標頭文字、各階段投票數）
@admin_settings_bp.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if request.method == 'POST':
        refresh_interval = request.form.get('refresh_interval')
        header_text = request.form.get('header_text')

        # 儲存 refresh_interval
        if refresh_interval:
            setting = Setting.query.filter_by(key='refresh_interval').first()
            if not setting:
                setting = Setting(key='refresh_interval')
                db.session.add(setting)
            setting.value = refresh_interval

        # 儲存 header_text
        if header_text:
            setting = Setting.query.filter_by(key='header_text').first()
            if not setting:
                setting = Setting(key='header_text')
                db.session.add(setting)
            setting.value = header_text

        db.session.commit()
        flash('✅ 系統基本設定已更新', 'success')
        return redirect(url_for('admin_settings.admin_settings'))

    # GET 顯示頁面
    phases = VotePhase.query.order_by(VotePhase.id).all()
    refresh_interval = get_setting('refresh_interval')
    header_text = get_setting('header_text')
    return render_template('admin_settings.html', phases=phases,
                           refresh_interval=refresh_interval,
                           header_text=header_text)

# ✅ 路由：更新各階段的 max_votes 設定
@admin_settings_bp.route('/admin/settings/update_max_votes', methods=['POST'])
def update_max_votes():
    for key, value in request.form.items():
        if key.startswith('max_votes_'):
            phase_id = int(key.split('_')[2])
            phase = VotePhase.query.get(phase_id)
            if phase:
                phase.max_votes = int(value)
    db.session.commit()
    flash('已更新各階段投票數上限')
    return redirect(url_for('admin_settings.admin_settings'))

# ✅ 路由：編輯各階段的名稱
@admin_settings_bp.route('/admin/settings/edit_phase_name/<int:phase_id>', methods=['GET', 'POST'])
def edit_phase_name(phase_id):
    phase = VotePhase.query.get_or_404(phase_id)
    if request.method == 'POST':
        new_name = request.form.get('name')
        if new_name:
            phase.name = new_name
            db.session.commit()
            flash('已更新階段名稱', 'success')
            return redirect(url_for('admin_settings.admin_settings'))
        else:
            flash('階段名稱不能為空', 'danger')
    return render_template('edit_phase_name.html', phase=phase)

# ✅ 路由：編輯教職員投票標題
@admin_settings_bp.route('/admin/settings/edit_staff_vote_title', methods=['GET', 'POST'])
def edit_staff_vote_title():
    setting = Setting.query.filter_by(key='staff_vote_title').first()
    if request.method == 'POST':
        new_title = request.form['title']
        if setting:
            setting.value = new_title
        else:
            setting = Setting(key='staff_vote_title', value=new_title)
            db.session.add(setting)
        db.session.commit()
        flash('已更新投票標題', 'success')
        return redirect(url_for('admin.admin_dashboard'))  # ✅ 修正導向
    return render_template('edit_staff_vote_title.html', setting=setting)
