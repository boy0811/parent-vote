from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class Candidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120), nullable=True)  # 改為允許為空
    class_name = db.Column(db.String(50), nullable=True)       # 孩子班級
    parent_name = db.Column(db.String(50), nullable=True)      # 家長姓名
    phase = db.Column(db.Integer, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
