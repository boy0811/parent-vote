from sqlalchemy import create_engine, text

# 指向你的資料庫
engine = create_engine("sqlite:///voting.db")

with engine.connect() as conn:
    conn.execute(text("DELETE FROM alembic_version"))
    conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('4a0458a75717')"))
    conn.commit()

print("✅ alembic_version 已重置為 4a0458a75717")
