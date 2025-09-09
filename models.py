from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# ----------------------
# 家長候選人模型
# ----------------------
class Candidate(db.Model):
    __tablename__ = 'candidate'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)  # 移除 unique=True
    password_hash = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=True)
    parent_name = db.Column(db.String(50), nullable=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('vote_phase.id', name='fk_candidate_phase'), default=1)
    has_voted = db.Column(db.Boolean, default=False)
    is_signed_in = db.Column(db.Boolean, default=False)
    signed_in_time = db.Column(db.DateTime, nullable=True)
    is_promoted = db.Column(db.Boolean, default=False)
    is_winner = db.Column(db.Boolean, default=False)
    promote_type = db.Column(db.String(10), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('username', 'phase_id', name='uq_username_phase'),
    )

    def set_password(self, password):
        # ✅ 降低迭代次數，避免 Render OOM
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:10000', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----------------------
# 家長投票紀錄
# ----------------------
class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidate.id'), nullable=False)
    phase_id = db.Column(db.Integer, db.ForeignKey('vote_phase.id'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('voter_id', 'candidate_id', 'phase_id', name='uix_vote_unique'),
    )

# ----------------------
# 投票階段模型
# ----------------------
class VotePhase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    is_open = db.Column(db.Boolean, default=False)
    max_votes = db.Column(db.Integer, default=1)
    min_votes = db.Column(db.Integer, default=1)  # 新增最小票數欄位
    promote_count = db.Column(db.Integer, default=1)
    candidates = db.relationship('Candidate', backref='vote_phase', lazy=True)

# ----------------------
# 系統設定
# ----------------------
class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(200), nullable=False)

# ----------------------
# 管理員帳號
# ----------------------
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:10000', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----------------------
# 教職員名單
# ----------------------
class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    class_name = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:10000', salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ----------------------
# 教職員投票紀錄
# ----------------------
class StaffVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'), nullable=False)
    vote_result = db.Column(db.String(10), nullable=False)
    reset_id = db.Column(db.Integer, nullable=False, default=1)

# ----------------------
# 操作紀錄
# ----------------------
class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20))  # admin/candidate/staff
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(255))  # 操作內容描述
    timestamp = db.Column(db.DateTime, default=datetime.now)  # 改為本地時間
    ip_address = db.Column(db.String(50))

    def __repr__(self):
        return f"<Log {self.user_type}-{self.user_id}: {self.action}>"
