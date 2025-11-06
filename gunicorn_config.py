"""
Gunicorn 配置文件
用於生產環境部署
"""
import multiprocessing

# 綁定地址和端口
bind = "127.0.0.1:8000"

# Worker 進程數（建議設置為 CPU 核心數 * 2 + 1）
workers = multiprocessing.cpu_count() * 2 + 1

# Worker 類型
worker_class = "sync"

# 每個 worker 的最大請求數，超過後重啟 worker（防止內存洩漏）
max_requests = 1000
max_requests_jitter = 50

# 超時設置（秒）
timeout = 30
keepalive = 2

# 日誌設置
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"

# 進程名稱
proc_name = "climbing_system_gunicorn"

# 守護進程模式（由 systemd 管理時設為 False）
daemon = False

# 用戶和組（需要時設置，通常由 systemd 管理）
# user = "www-data"
# group = "www-data"

# 工作目錄
chdir = "/var/www/climbing_score_counting_system"

# Python 路徑
pythonpath = "/var/www/climbing_score_counting_system"

# 預加載應用（提高性能，但可能導致內存使用增加）
preload_app = True

# 優雅重啟
graceful_timeout = 30

