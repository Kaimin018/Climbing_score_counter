"""
Django settings for climbing_system project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# 從環境變數讀取，如果沒有則使用開發環境的預設值
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-climbing-score-system-dev-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
# 生產環境請設置環境變數 DEBUG=False
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

# 從環境變數讀取允許的主機，如果沒有則允許所有（僅開發環境）
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',') if os.environ.get('ALLOWED_HOSTS') else ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'scoring',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'climbing_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'climbing_system.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# 預設使用 SQLite（無需額外設置，適合快速測試）
# 如需使用 MySQL，請註釋掉 SQLite 配置並取消註釋 MySQL 配置

# SQLite 配置（預設）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        # 添加测试数据库配置，使用内存数据库加速测试
        'TEST': {
            'NAME': ':memory:',  # 使用内存数据库，速度更快
        },
    }
}

# MySQL 配置（如需使用，請取消註釋並註釋掉上面的 SQLite 配置）
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'climbing_score_db',
#         'USER': 'root',
#         'PASSWORD': '',  # 請填入您的 MySQL 密碼
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'charset': 'utf8mb4',
#         },
#     }
# }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'zh-hant'

TIME_ZONE = 'Asia/Taipei'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
# 生產環境靜態文件收集目錄
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (用戶上傳的文件)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
# 生產環境建議設置具體的允許來源
CORS_ALLOW_ALL_ORIGINS = os.environ.get('CORS_ALLOW_ALL_ORIGINS', 'True') == 'True'
if not CORS_ALLOW_ALL_ORIGINS:
    cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', '')
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',  # 支持文件上傳
        'rest_framework.parsers.FormParser',
    ],
    # 認證設置
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    # 權限設置：開發環境允許所有操作，生產環境區分訪客和成員
    # 訪客只能讀取，普通成員可以讀寫
    'DEFAULT_PERMISSION_CLASSES': (
        ['rest_framework.permissions.AllowAny'] if DEBUG 
        else ['scoring.permissions.IsMemberOrReadOnly']
    ),
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'detailed': {
            'format': '{levelname} {asctime} {name} {pathname}:{lineno} {funcName}() {process:d} {thread:d}\n{message}',
            'style': '{',
        },
        'exception': {
            'format': '{levelname} {asctime} {name} {pathname}:{lineno} {funcName}() {process:d} {thread:d}\n{message}\n{exc_info}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'scoring': {
            'handlers': ['console'],
            'level': 'DEBUG',  # 改為 DEBUG 以顯示所有日誌
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# 配置文件日誌（支持桌面和移動設備）
def get_logs_directory():
    """
    獲取日誌目錄路徑，支持多種平台：
    - 桌面/服務器：使用項目根目錄下的 logs/ 目錄
    - Android：使用應用數據目錄
    - iOS：使用 Documents 目錄
    - 其他：嘗試使用項目目錄，失敗則使用臨時目錄
    """
    import os
    import platform
    from pathlib import Path
    
    # 檢查是否為移動設備環境
    is_mobile = False
    mobile_logs_dir = None
    
    # Android 環境檢測
    android_data_dir = os.environ.get('ANDROID_DATA')
    if android_data_dir:
        try:
            # Android 應用數據目錄
            app_data_dir = Path(android_data_dir) / 'data' / 'climbing_system' / 'logs'
            app_data_dir.mkdir(parents=True, exist_ok=True)
            mobile_logs_dir = app_data_dir
            is_mobile = True
        except:
            pass
    
    # iOS 環境檢測（通過環境變數或路徑判斷）
    ios_documents = os.environ.get('IOS_DOCUMENTS_DIR')
    if ios_documents:
        try:
            ios_logs_dir = Path(ios_documents) / 'logs'
            ios_logs_dir.mkdir(parents=True, exist_ok=True)
            mobile_logs_dir = ios_logs_dir
            is_mobile = True
        except:
            pass
    
    # 如果檢測到移動設備，使用移動設備目錄
    if is_mobile and mobile_logs_dir:
        return mobile_logs_dir
    
    # 桌面/服務器環境：使用項目根目錄
    try:
        logs_dir = BASE_DIR / 'logs'
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    except (OSError, PermissionError):
        # 如果無法創建項目目錄，使用臨時目錄
        import tempfile
        temp_logs_dir = Path(tempfile.gettempdir()) / 'climbing_system_logs'
        try:
            temp_logs_dir.mkdir(parents=True, exist_ok=True)
            return temp_logs_dir
        except:
            # 最後的備選方案：使用當前工作目錄
            return Path.cwd() / 'logs'

# 嘗試創建日誌目錄並添加文件日誌處理器
# 在 DEBUG 模式下也生成日誌文件（方便調試，特別是移動設備）
try:
    logs_dir = get_logs_directory()
    log_file_path = logs_dir / 'django.log'
    
    # 確保目錄存在
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    # 添加文件日誌處理器（支持日誌輪轉，避免文件過大）
    from logging.handlers import RotatingFileHandler
    
    LOGGING['handlers']['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': str(log_file_path),
        'formatter': 'detailed',
        'level': 'DEBUG',
        'maxBytes': 10 * 1024 * 1024,  # 10MB
        'backupCount': 5,  # 保留 5 個備份文件
        'encoding': 'utf-8',  # 支持中文日誌
    }
    
    # 為所有環境添加文件日誌處理器（包括 DEBUG 模式）
    LOGGING['loggers']['scoring']['handlers'].append('file')
    LOGGING['loggers']['django']['handlers'].append('file')
    
    # 記錄日誌文件位置（僅在首次配置時）
    import logging
    logger = logging.getLogger('scoring')
    logger.info(f"日誌文件已配置，保存位置: {log_file_path}")
    
except (OSError, PermissionError) as e:
    # 如果無法創建日誌文件，只使用控制台日誌
    import warnings
    warnings.warn(f"無法創建日誌文件 {log_file_path if 'log_file_path' in locals() else 'logs/django.log'}: {e}。將只使用控制台日誌。")

# Session 配置（適用於所有環境）
# 確保 session cookie 可以正常工作
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'  # 允許跨站請求時發送 cookie
SESSION_COOKIE_AGE = 86400  # 24 小時
SESSION_SAVE_EVERY_REQUEST = False

# 生產環境安全設置
if not DEBUG:
    # 是否使用 HTTPS（如果已配置 SSL 證書，設為 True）
    USE_HTTPS = os.environ.get('USE_HTTPS', 'False') == 'True'
    SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
    
    # Cookie 安全設置：只有在使用 HTTPS 時才設置為 True
    # 如果使用 HTTP，設為 False 以確保 Cookie 可以正常設置
    SESSION_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SECURE = USE_HTTPS
    CSRF_COOKIE_SAMESITE = 'Lax'  # 確保 CSRF cookie 可以正常發送
    
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

