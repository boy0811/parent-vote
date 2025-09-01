from flask import Blueprint

main_routes = Blueprint('main_routes', __name__)


@main_routes.route('/')
def home():
    return "首頁：歡迎使用投票系統（可改為 render_template('home.html')）"
