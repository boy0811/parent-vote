from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from ..models import Candidate, db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        candidate = Candidate.query.filter_by(username=username).first()

        if candidate:
            if check_password_hash(candidate.password_hash, password):
                session['candidate_id'] = candidate.id

                if not candidate.class_name or not candidate.parent_name:
                    return redirect(url_for('auth.confirm_candidate'))

                return redirect(url_for('auth.vote'))  # ✅ 改這裡
            else:
                flash('密碼錯誤', 'danger')
        else:
            flash('帳號不存在，請聯繫管理員', 'danger')

    return render_template('login.html')


@auth_bp.route('/confirm', methods=['GET', 'POST'])
def confirm_candidate():
    if 'temp_username' not in session:
        return redirect(url_for('auth.login'))

    temp_username = session['temp_username']
    temp_existing = session.get('temp_existing', False)

    if request.method == 'POST':
        class_name = request.form.get('class_name')
        parent_name = request.form.get('parent_name')
        name = request.form.get('name', '')

        try:
            if temp_existing:
                candidate = Candidate.query.filter_by(username=temp_username).first()
                candidate.class_name = class_name
                candidate.parent_name = parent_name
            else:
                if not name:
                    flash("請填寫候選人姓名", "danger")
                    return redirect(url_for('auth.login'))

                existing = Candidate.query.filter_by(username=temp_username).first()
                if existing:
                    flash('該帳號已存在，請重新登入', 'danger')
                    return redirect(url_for('auth.login'))

                candidate = Candidate(
                    username=temp_username,
                    password_hash=session['temp_password'],
                    name=name,
                    class_name=class_name,
                    parent_name=parent_name,
                    phase=1
                )
                db.session.add(candidate)

            db.session.commit()
            session['candidate_id'] = candidate.id
            session.pop('temp_username', None)
            session.pop('temp_password', None)
            session.pop('temp_existing', None)

            return redirect(url_for('auth.vote'))  # ✅ 改這裡

        except Exception:
            flash("資料儲存失敗，請重新登入", "danger")
            return redirect(url_for('auth.login'))

    return render_template('confirm.html', username=temp_username, temp_existing=temp_existing, name='')
