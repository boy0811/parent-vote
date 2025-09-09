import pandas as pd
import os
from app import db
from models import Candidate, Staff, Admin

INPUT_FILE = "accounts.xlsx"  # 也可以改成 CSV

def load_accounts(file_path):
    """讀取 Excel 或 CSV，支援 帳號/密碼/班級/家長姓名"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xlsx":
        df = pd.read_excel(file_path, dtype=str).fillna("")
    elif ext == ".csv":
        df = pd.read_csv(file_path, dtype=str).fillna("")
    else:
        raise ValueError("只支援 Excel (.xlsx) 或 CSV (.csv) 檔案")

    # 檢查必要欄位
    required = {"帳號", "密碼"}
    if not required.issubset(df.columns):
        raise ValueError("檔案必須包含『帳號』和『密碼』欄位")

    return df

def update_passwords(file_path=INPUT_FILE):
    df = load_accounts(file_path)
    updated, skipped = 0, 0

    for _, row in df.iterrows():
        username = row["帳號"].strip()
        password = row["密碼"].strip()
        class_name = row.get("班級", "").strip()
        parent_name = row.get("家長姓名", "").strip()

        if not username or not password:
            skipped += 1
            print(f"⚠️ 跳過：缺少帳號或密碼 -> {row}")
            continue

        user = Candidate.query.filter_by(username=username).first()
        if not user:
            user = Staff.query.filter_by(username=username).first()
        if not user:
            user = Admin.query.filter_by(username=username).first()

        if user:
            user.set_password(password)

            # ✅ 如果是 Candidate，順便更新班級與家長姓名
            if isinstance(user, Candidate):
                if class_name:
                    user.class_name = class_name
                if parent_name:
                    user.name = parent_name
                    user.parent_name = parent_name

            updated += 1
            print(f"✅ 已更新 {username}")
        else:
            skipped += 1
            print(f"❌ 找不到帳號：{username}")

    db.session.commit()
    print("🎉 更新完成")
    print(f"👉 成功更新：{updated} 筆, 跳過/錯誤：{skipped} 筆")

if __name__ == "__main__":
    try:
        update_passwords(INPUT_FILE)
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
