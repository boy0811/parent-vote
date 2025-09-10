from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Setting, VotePhase, Vote, Candidate
import os
import shutil
import datetime

admin_settings_bp = Blueprint('admin_settings', __name__)

from sqlalchemy import func  # 若檔案頂端還沒有就補上

@admin_settings_bp.route('/settings', methods=['GET', 'POST'], endpoint='admin_settings')
def admin_settings():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    # 1️⃣ 取得現有設定
    refresh_setting       = Setting.query.filter_by(key='refresh_interval').first()
    slide_setting         = Setting.query.filter_by(key='slide_interval').first()   # ← 新增
    staff_title_setting   = Setting.query.filter_by(key='staff_vote_title').first()
    parent_title_setting  = Setting.query.filter_by(key='parent_vote_title').first()
    vote_title_setting    = Setting.query.filter_by(key='vote_title').first()
    current_phase_setting = Setting.query.filter_by(key='current_phase_id').first()

    refresh_value   = refresh_setting.value if refresh_setting else '10'
    slide_interval  = slide_setting.value   if slide_setting   else '5'            # ← 新增
    staff_vote_title  = staff_title_setting.value  if staff_title_setting  else '教職員投票'
    parent_vote_title = parent_title_setting.value if parent_title_setting else '家長投票'
    vote_title        = vote_title_setting.value   if vote_title_setting   else '第一階段：家長委員（最多 6 票）'
    current_phase_id  = current_phase_setting.value if current_phase_setting else ''

    phases = VotePhase.query.order_by(VotePhase.id).all()

    # 2️⃣ 處理表單提交
    if request.method == 'POST':
        # ➔ 自動刷新秒數（票數刷新）
        refresh_interval = (request.form.get('refresh_interval', '') or '').strip()
        save_setting('refresh_interval', refresh_interval or '10')

        # ➔ 輪播間隔秒數（新增）
        slide_interval_form = (request.form.get('slide_interval', '') or '').strip()
        save_setting('slide_interval', slide_interval_form or '5')

        # ➔ 投票標題
        staff_title = (request.form.get('staff_vote_title', '') or '').strip()
        save_setting('staff_vote_title', staff_title)

        parent_title = (request.form.get('parent_vote_title', '') or '').strip()
        save_setting('parent_vote_title', parent_title)

        vote_title_val = (request.form.get('vote_title', '') or '').strip()
        save_setting('vote_title', vote_title_val)

        # ➔ 當前階段 ID
        selected_phase_id = (request.form.get('current_phase_id', '') or '').strip()
        save_setting('current_phase_id', selected_phase_id)

        # ➔ 各階段投票數與晉級人數
        for phase in phases:
            max_votes = (request.form.get(f'max_votes_{phase.id}', '') or '').strip()
            promote_count = (request.form.get(f'promote_count_{phase.id}', '') or '').strip()

            try:
                phase.max_votes = int(max_votes)
            except (ValueError, TypeError):
                phase.max_votes = 1

            try:
                phase.promote_count = int(promote_count)
            except (ValueError, TypeError):
                phase.promote_count = 1

        db.session.commit()
        flash('✅ 系統設定已更新', 'success')
        return redirect(url_for('admin_settings.admin_settings'))

    return render_template('admin_settings.html',
                           refresh_value=refresh_value,
                           slide_interval=slide_interval,              # ← 傳到模板
                           staff_vote_title=staff_vote_title,
                           parent_vote_title=parent_vote_title,
                           vote_title=vote_title,
                           current_phase_id=current_phase_id,
                           phases=phases,
                           all_phases=phases)

# 🛠️ 通用儲存設定
def save_setting(key, value):
    setting = Setting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    db.session.commit()

# 🧹 清除指定階段資料
@admin_settings_bp.route('/clear_phase_data', methods=['POST'], endpoint='clear_phase_data')
def clear_phase_data():
    phase_id = request.form.get("phase_id", type=int)
    if not phase_id:
        flash("⚠️ 請選擇要清除的階段", "warning")
        return redirect(url_for('admin_settings.admin_settings'))

    vote_deleted = Vote.query.filter_by(phase_id=phase_id).delete()
    candidates = Candidate.query.filter_by(phase_id=phase_id).all()
    candidate_count = len(candidates)
    for c in candidates:
        db.session.delete(c)

    db.session.commit()
    flash(f"✅ 已成功清除階段 ID {phase_id} 的候選人（{candidate_count} 筆）與投票紀錄（{vote_deleted} 筆）", "success")
    return redirect(url_for('admin_settings.admin_settings'))

# 🧹 一鍵清除所有資料
@admin_settings_bp.route('/clear_all_data', methods=['POST'], endpoint='clear_all_data')
def clear_all_data():
    from models import OperationLog, User, Admin

    confirm_text = request.form.get('confirm_delete', '').strip()
    if confirm_text != 'DELETE':
        flash("⚠️ 驗證字串錯誤，未執行清空動作。", "warning")
        return redirect(url_for('admin_settings.admin_settings'))

    # 🔹 清空主要表
    vote_deleted = Vote.query.delete()
    candidate_deleted = Candidate.query.delete()
    phase_deleted = VotePhase.query.delete()
    setting_deleted = Setting.query.delete()
    log_deleted = OperationLog.query.delete()
    user_deleted = User.query.delete()
    admin_deleted = Admin.query.delete()

    db.session.commit()

    # 🔹 建立預設管理員
    default_admin = Admin(username="admin")
    default_admin.set_password("1234")
    db.session.add(default_admin)
    db.session.commit()

    flash(f"""🧹 已清除所有資料：
    - 投票紀錄 {vote_deleted} 筆
    - 候選人 {candidate_deleted} 筆
    - 階段 {phase_deleted} 筆
    - 系統設定 {setting_deleted} 筆
    - 操作紀錄 {log_deleted} 筆
    - 使用者帳號 {user_deleted} 筆
    - 管理員帳號 {admin_deleted} 筆
    ✅ 已建立預設管理員：帳號 admin / 密碼 1234
    """, "success")

    return redirect(url_for('admin_settings.admin_settings'))

# ✅ 備份資料庫功能

@admin_settings_bp.route('/backup_db', methods=['POST'], endpoint='backup_db')
def backup_db():
    if 'admin' not in session:
        return redirect(url_for('admin_auth.admin_login'))

    if not os.path.exists("backup"):
        os.makedirs("backup")

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    src = "voting.db"
    dest = f"backup/voting_backup_{timestamp}.db"
    try:
        shutil.copy(src, dest)
        flash(f"✅ 資料庫已備份：{dest}", "success")
    except Exception as e:
        flash(f"❌ 備份失敗：{str(e)}", "danger")

    return redirect(url_for('admin_settings.admin_settings'))
