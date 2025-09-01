# checkin/__init__.py
from .checkin_panel import checkin_panel_bp

def register_checkin_blueprints(app):
    """在 app.py 裡呼叫這個函式即可一次註冊簽到相關的 Blueprints"""
    app.register_blueprint(checkin_panel_bp)  # /checkin_panel/...
