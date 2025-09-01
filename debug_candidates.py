# debug_candidates.py

from app import app, db
from models import Candidate
from utils.helpers import get_grade_from_class

with app.app_context():
    candidates = Candidate.query.all()
    for c in candidates:
        print(f"{c.id}｜{c.class_name}｜{get_grade_from_class(c.class_name)}｜{c.parent_name}")
