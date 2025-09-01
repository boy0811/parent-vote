# generate_cert.py
import os
import shutil

try:
    from werkzeug.serving import make_ssl_devcert
except ImportError:
    raise SystemExit("請先安裝 werkzeug：pip install werkzeug")

# 改成你的專案路徑
PROJECT_DIR = r"C:\Users\user\Desktop\voting_system"
HOST = "192.168.0.116"  # 你區網伺服器的 IP

os.chdir(PROJECT_DIR)

base = "devcert"
# 會產生 devcert.crt / devcert.key
make_ssl_devcert(base, host=HOST)

# 轉存成 Flask 習慣用的檔名 cert.pem / key.pem
shutil.copyfile(base + ".crt", "cert.pem")
shutil.copyfile(base + ".key", "key.pem")

print("已在此資料夾產生 cert.pem 與 key.pem")
