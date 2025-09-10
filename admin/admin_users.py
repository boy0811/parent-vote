# admin_users.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Candidate

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/admin")

# ----------------------
# 帳號列表
# ----------------------
@admin_users_bp.route("/users")
def user_list():
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    users = User.query.all()
    return render_template("admin_users.html", users=users)


# ----------------------
# 新增帳號
# ----------------------
@admin_users_bp.route("/users/add", methods=["GET", "POST"])
def add_user():
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    candidates = Candidate.query.all()

    if request.method == "POST":
        user = User(
            username=request.form["username"],
            candidate_id=int(request.form["candidate_id"]),
        )
        user.set_password(request.form["password"])
        db.session.add(user)
        db.session.commit()
        flash("✅ 帳號新增成功", "success")
        return redirect(url_for("admin_users.user_list"))

    return render_template("admin_user_form.html", user=None, candidates=candidates)


# ----------------------
# 編輯帳號
# ----------------------
@admin_users_bp.route("/users/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    user = User.query.get_or_404(user_id)
    candidates = Candidate.query.all()

    if request.method == "POST":
        user.username = request.form["username"]
        user.candidate_id = int(request.form["candidate_id"])
        if request.form["password"]:
            user.set_password(request.form["password"])
        db.session.commit()
        flash("✅ 帳號修改成功", "success")
        return redirect(url_for("admin_users.user_list"))

    return render_template("admin_user_form.html", user=user, candidates=candidates)


# ----------------------
# 刪除單一帳號
# ----------------------
@admin_users_bp.route("/users/delete/<int:user_id>")
def delete_user(user_id):
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("✅ 帳號刪除成功", "info")
    return redirect(url_for("admin_users.user_list"))


# ----------------------
# 批次刪除帳號
# ----------------------
@admin_users_bp.route("/users/delete", methods=["POST"])
def delete_users():
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    ids = request.form.getlist("user_ids")
    if ids:
        try:
            ids = [int(i) for i in ids]
            User.query.filter(User.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
            flash(f"✅ 已成功刪除 {len(ids)} 個帳號", "success")
        except ValueError:
            db.session.rollback()
            flash("❌ 帳號 ID 格式錯誤", "danger")
    else:
        flash("⚠️ 請選擇要刪除的帳號", "warning")

    return redirect(url_for("admin_users.user_list"))

# 匯入帳號
@admin_users_bp.route("/users/import", methods=["GET", "POST"])
def import_users():
    if "admin" not in session:
        return redirect(url_for("admin_auth.admin_login"))

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("請選擇檔案", "danger")
            return redirect(url_for("admin_users.import_users"))

        ext = file.filename.lower().split(".")[-1]
        try:
            # CSV
            if ext == "csv":
                import csv, chardet
                raw = file.read()
                result = chardet.detect(raw)
                encoding = result["encoding"] or "utf-8"
                file.stream.seek(0)

                reader = csv.DictReader(
                    (line.decode(encoding, errors="ignore") for line in file.stream)
                )
                rows = list(reader)
            else:
                import pandas as pd
                df = pd.read_excel(file, dtype=str, engine="openpyxl").fillna("")
                rows = df.to_dict(orient="records")
        except Exception as e:
            flash(f"❌ 讀取檔案失敗：{e}", "danger")
            return redirect(url_for("admin_users.import_users"))

        required_cols = {"帳號", "密碼"}
        if not rows or not required_cols.issubset(rows[0].keys()):
            flash(f"❌ 匯入失敗：缺少必要欄位 {required_cols}", "danger")
            return redirect(url_for("admin_users.import_users"))

        created, updated, skipped = 0, 0, 0
        from models import User
        try:
            for row in rows:
                username = (row.get("帳號") or "").strip()
                password = str(row.get("密碼") or "").strip() or "1234"

                if not username:
                    skipped += 1
                    continue

                user = User.query.filter_by(username=username).first()
                if user:
                    user.set_password(password)
                    updated += 1
                else:
                    user = User(username=username)
                    user.set_password(password)
                    db.session.add(user)
                    created += 1

            db.session.commit()
            flash(f"✅ 匯入完成：新增 {created} 筆、更新 {updated} 筆、略過 {skipped} 筆", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"❌ 匯入失敗並已回滾：{e}", "danger")

        return redirect(url_for("admin_users.user_list"))

    return render_template("admin_import_users.html")
