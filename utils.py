# utils.py
from models import Setting

def get_setting(key, default=''):
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default
