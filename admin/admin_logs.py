from flask import Blueprint, render_template, request, Response, jsonify
from sqlalchemy import or_
from datetime import datetime
import csv

from models import db, OperationLog

admin_logs_bp = Blueprint('admin_logs', __name__)

# ---------------------------
# 頁面（不再把 logs 傳進去，交給 DataTables AJAX 取得）
# ---------------------------
@admin_logs_bp.route('/logs')
def view_logs():
    # 這裡仍保留原本的 query string 以便模板顯示（不需要也可移除）
    return render_template(
        'admin_logs.html',
        user_type=request.args.get('user_type', ''),
        keyword=request.args.get('keyword', ''),
        date_from=request.args.get('date_from', ''),
        date_to=request.args.get('date_to', '')
    )

# ---------------------------
# DataTables Server-Side API
# ---------------------------
@admin_logs_bp.route('/logs/data')
def logs_data():
    # DataTables 參數
    draw   = int(request.args.get('draw', '1'))
    start  = int(request.args.get('start', '0'))
    length = int(request.args.get('length', '25'))
    search_value = request.args.get('search[value]', '')

    # 自訂篩選參數（來自表單）
    user_type = request.args.get('user_type', '').strip()
    keyword   = request.args.get('keyword', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to   = request.args.get('date_to', '').strip()

    # 排序
    order_column_index = request.args.get('order[0][column]', '0')
    order_dir = request.args.get('order[0][dir]', 'desc')
    columns = ['timestamp', 'user_type', 'user_id', 'action', 'ip_address']
    order_column = columns[int(order_column_index)] if order_column_index.isdigit() else 'timestamp'

    q = OperationLog.query

    # 自訂篩選
    if user_type:
        q = q.filter(OperationLog.user_type == user_type)

    if keyword:
        like = f"%{keyword}%"
        q = q.filter(or_(
            OperationLog.action.ilike(like),
            OperationLog.ip_address.ilike(like)
        ))

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            q = q.filter(OperationLog.timestamp >= dt_from)
        except Exception:
            pass

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            q = q.filter(OperationLog.timestamp <= dt_to)
        except Exception:
            pass

    # 全量與篩選後數量
    total_records = OperationLog.query.count()
    filtered_records = q.count()

    # 排序
    col_attr = getattr(OperationLog, order_column)
    q = q.order_by(col_attr.desc() if order_dir == 'desc' else col_attr.asc())

    # 分頁
    logs = q.offset(start).limit(length).all()

    data = []
    for log in logs:
        data.append([
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            log.user_type,
            log.user_id,
            log.action,
            log.ip_address or ""
        ])

    return jsonify({
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': filtered_records,
        'data': data
    })

# ---------------------------
# 匯出 CSV（後端全量）
# ---------------------------
@admin_logs_bp.route('/logs/export')
def export_logs_csv():
    q = OperationLog.query.order_by(OperationLog.timestamp.desc())

    class Echo:
        def write(self, value):
            return value

    def generate():
        writer = csv.writer(Echo())
        yield writer.writerow(["時間", "使用者類型", "使用者ID", "操作", "IP"])
        for log in q:
            yield writer.writerow([
                log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                log.user_type,
                log.user_id,
                log.action,
                log.ip_address or ""
            ])

    return Response(generate(),
                    mimetype='text/csv',
                    headers={"Content-Disposition": "attachment; filename=operation_logs.csv"})
