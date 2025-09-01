from sqlalchemy import create_engine, text

# 資料庫連線路徑（SQLite 預設）
engine = create_engine('sqlite:///voting.db')

with engine.connect() as conn:
    try:
        conn.execute(text("DROP TABLE IF EXISTS _alembic_tmp_candidate"))
        print("✅ 已成功刪除 _alembic_tmp_candidate")
    except Exception as e:
        print("⚠️ 刪除時發生錯誤：", e)
