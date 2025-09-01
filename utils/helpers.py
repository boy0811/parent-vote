# utils/helpers.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
from typing import Any, Dict, Tuple

from flask import request
from models import db, Setting

# --------------------------------------------------
# Optional: OperationLog（若專案還沒建此模型，不會爆炸）
# --------------------------------------------------
try:
    from models import OperationLog
    HAS_OPERATION_LOG = True
except Exception:
    HAS_OPERATION_LOG = False

# --------------------------------------------------
# 🔧 系統設定快取
# --------------------------------------------------
_setting_cache: Dict[str, Any] = {}

def get_setting(key: str, default: Any = None, use_cache: bool = True) -> Any:
    """
    取得系統設定值（含記憶體快取）。
    """
    if use_cache and key in _setting_cache:
        return _setting_cache[key]

    setting = Setting.query.filter_by(key=key).first()
    value = setting.value if setting else default
    if use_cache:
        _setting_cache[key] = value
    return value

def set_setting(key: str, value: str) -> None:
    """
    儲存系統設定值，並同步更新快取。
    """
    s = Setting.query.filter_by(key=key).first()
    if s:
        s.value = value
    else:
        s = Setting(key=key, value=value)
        db.session.add(s)
    db.session.commit()
    _setting_cache[key] = value

# --------------------------------------------------
# 🏷️ 年級對應 & 分組
# --------------------------------------------------
GRADE_ORDER = [
    "幼兒園", "一年級", "二年級", "三年級",
    "四年級", "五年級", "六年級", "其他"
]

def get_grade_from_class(class_name: str | None) -> str:
    """
    根據班級代碼（例如 '001', '101', '202'）回傳對應的年級名稱。
    幼兒園為班級代碼 001~020 或 class_name 包含「幼」字。
    """
    if not class_name:
        return "其他"

    if "幼" in class_name:
        return "幼兒園"

    stripped = class_name.lstrip("0")
    if stripped == "":
        return "其他"

    try:
        code = int(stripped)
        if 1 <= code <= 20:
            return "幼兒園"
        elif 100 <= code <= 199:
            return "一年級"
        elif 200 <= code <= 299:
            return "二年級"
        elif 300 <= code <= 399:
            return "三年級"
        elif 400 <= code <= 499:
            return "四年級"
        elif 500 <= code <= 599:
            return "五年級"
        elif 600 <= code <= 699:
            return "六年級"
        else:
            return "其他"
    except ValueError:
        return "其他"

def group_candidates_by_grade(candidates) -> "OrderedDict[str, list]":
    """
    傳入候選人清單，依 class_name 對應年級分組。
    以固定 GRADE_ORDER 輸出；不在表內者放最後。
    """
    grouped = defaultdict(list)
    for c in candidates:
        grade = get_grade_from_class(getattr(c, "class_name", None))
        grouped[grade].append(c)

    ordered = OrderedDict()
    for g in GRADE_ORDER:
        if g in grouped:
            ordered[g] = grouped[g]

    for g in grouped:
        if g not in ordered:
            ordered[g] = grouped[g]

    return ordered

# --------------------------------------------------
# 💾 資料庫備份（含自動清理舊檔）
# --------------------------------------------------
def backup_database(db_path: str = "instance/voting.db",
                    backup_dir: str = "backup",
                    keep_days: int = 7) -> str:
    """
    將 DB 檔案備份至 backup/，檔名帶時間戳；並清理過期備份。
    回傳備份檔完整路徑。
    """
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"voting_backup_{timestamp}.db")

    # 先確保 session 落盤
    try:
        db.session.commit()
    except Exception:
        pass

    shutil.copy(db_path, dest)

    # 清理舊備份
    cutoff = datetime.now() - timedelta(days=keep_days)
    for f in os.listdir(backup_dir):
        if not f.startswith("voting_backup_") or not f.endswith(".db"):
            continue
        full = os.path.join(backup_dir, f)
        try:
            ts = f.replace("voting_backup_", "").replace(".db", "")
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            if dt < cutoff:
                os.remove(full)
        except Exception:
            # 檔名格式不合，略過
            continue

    return dest

# --------------------------------------------------
# 📝 中文化操作紀錄
# --------------------------------------------------
METHOD_ZH = {
    "GET": "瀏覽",
    "POST": "提交",
    "PUT": "更新",
    "DELETE": "刪除",
    "PATCH": "修改",
}

# 依 endpoint 映射中文（請視你的專案擴充）
ENDPOINT_ZH = {
    # auth
    "admin_auth.admin_login": "管理員登入",
    "admin_auth.admin_logout": "管理員登出",

    # settings
    "admin_settings.admin_settings": "更新系統設定",
    "admin_settings.backup_db": "備份資料庫",
    "admin_settings.clear_phase_data": "清除指定階段資料",
    "admin_settings.clear_all_data": "一鍵清空所有資料",

    # logs
    "admin_logs.view_logs": "查看操作紀錄",
    "admin_logs.logs_data": "查詢操作紀錄（資料表）",
    "admin_logs.export_logs_csv": "匯出操作紀錄 CSV",

    # votes
    "admin_votes.admin_live_votes": "即時監票頁",
    "admin_votes.admin_winners": "查看得票結果",
    "admin_votes.manage_vote_phases": "投票階段管理頁",
    "admin_votes.toggle_vote_phase": "切換投票階段開關",
    "admin_votes.close_all_phases": "關閉所有投票階段",
    "admin_votes.reset_vote_phases": "重設所有投票階段",
    "admin_votes.clear_parent_votes": "清空家長會票數",
    "admin_votes.close_phase": "關閉目前階段",
    "admin_votes.open_phase": "開啟指定階段",
    "admin_votes.open_next_phase": "開啟下一階段",
    "admin_votes.admin_tiebreaker": "同票手動晉級處理",
    "admin_votes.votes_log": "查看投票明細（誰投給誰）",

    # 其他自行補上...
}

SENSITIVE_KEYS = {"password", "password1", "password2", "csrf_token"}

def _sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    if not d:
        return {}
    return {k: ("***" if k.lower() in SENSITIVE_KEYS else v) for k, v in d.items()}

def zh_action_from_request(req) -> str:
    """
    把 request 轉成中文敘述字串（遮蔽敏感欄位）。
    """
    method_zh = METHOD_ZH.get(req.method, req.method)
    endpoint = (req.endpoint or "").strip()

    # 1) 以 endpoint 對應中文（較精準）
    base = ENDPOINT_ZH.get(endpoint)
    if base:
        action = f"{base}（{method_zh}）"
    else:
        # 2) fallback: 用路徑
        action = f"{method_zh} {req.path}"

    # 針對變更性操作加上精簡參數
    if req.method in ("POST", "PUT", "PATCH", "DELETE"):
        form_data = _sanitize_dict(req.form.to_dict())
        json_data = _sanitize_dict((req.get_json(silent=True) or {}))
        if form_data:
            action += f"｜表單：{form_data}"
        if json_data:
            action += f"｜JSON：{json_data}"

    return action

def add_log(user_type: str, user_id: int | None, action: str) -> None:
    """
    寫入操作紀錄（以本地時間記錄）。
    user_type: 'admin' / 'candidate' / 'staff' / 'guest'
    """
    if not HAS_OPERATION_LOG:
        return

    log = OperationLog(
        user_type=user_type,
        user_id=user_id,
        action=action,
        ip_address=request.remote_addr if request else None,
        timestamp=datetime.now()
    )
    db.session.add(log)
    db.session.commit()

# --------------------------------------------------
# 👮 供 before_request 使用的輔助
# --------------------------------------------------
def get_request_user(session) -> Tuple[str, int | None]:
    """
    從 session 判斷目前請求的使用者身份（admin/candidate/staff/guest）
    """
    if session.get("admin_id"):
        return "admin", session["admin_id"]
    if session.get("candidate_id"):
        return "candidate", session["candidate_id"]
    if session.get("staff_id"):
        return "staff", session["staff_id"]
    return "guest", None

def should_log_request(req, exclude_prefixes=("/static",), exclude_endpoints: set[str] | None = None) -> bool:
    """
    判斷此 request 是否要記錄（例如排除靜態資源、某些端點）。
    預設只記錄 POST/PUT/PATCH/DELETE。
    """
    if req.method not in ("POST", "PUT", "DELETE", "PATCH"):
        return False
    if any(req.path.startswith(p) for p in exclude_prefixes):
        return False
    if exclude_endpoints and req.endpoint in exclude_endpoints:
        return False
    return True
