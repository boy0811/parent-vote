from . import db

class VotePhase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='closed')  # 'open' or 'closed'
    max_votes = db.Column(db.Integer, default=1)  # 每階段最多可投幾票
