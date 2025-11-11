"""
工具函數：用於移動設備和桌面環境的通用功能
"""
import os
import platform
from pathlib import Path
from django.conf import settings


def get_logs_directory():
    """
    獲取日誌目錄路徑，支持多種平台：
    - 桌面/服務器：使用項目根目錄下的 logs/ 目錄
    - Android：使用應用數據目錄（通過環境變數 ANDROID_DATA）
    - iOS：使用 Documents 目錄（通過環境變數 IOS_DOCUMENTS_DIR）
    - 其他：嘗試使用項目目錄，失敗則使用臨時目錄
    
    返回:
        Path: 日誌目錄的 Path 對象
    """
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
        except Exception:
            pass
    
    # iOS 環境檢測（通過環境變數或路徑判斷）
    ios_documents = os.environ.get('IOS_DOCUMENTS_DIR')
    if ios_documents:
        try:
            ios_logs_dir = Path(ios_documents) / 'logs'
            ios_logs_dir.mkdir(parents=True, exist_ok=True)
            mobile_logs_dir = ios_logs_dir
            is_mobile = True
        except Exception:
            pass
    
    # 如果檢測到移動設備，使用移動設備目錄
    if is_mobile and mobile_logs_dir:
        return mobile_logs_dir
    
    # 桌面/服務器環境：使用項目根目錄
    try:
        logs_dir = settings.BASE_DIR / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        return logs_dir
    except (OSError, PermissionError):
        # 如果無法創建項目目錄，使用臨時目錄
        import tempfile
        temp_logs_dir = Path(tempfile.gettempdir()) / 'climbing_system_logs'
        try:
            temp_logs_dir.mkdir(parents=True, exist_ok=True)
            return temp_logs_dir
        except Exception:
            # 最後的備選方案：使用當前工作目錄
            return Path.cwd() / 'logs'


def get_log_file_path():
    """
    獲取日誌文件的完整路徑
    
    返回:
        str: 日誌文件的完整路徑
    """
    logs_dir = get_logs_directory()
    return str(logs_dir / 'django.log')


def is_mobile_device():
    """
    檢測是否在移動設備上運行
    
    返回:
        bool: 如果是移動設備返回 True，否則返回 False
    """
    android_data_dir = os.environ.get('ANDROID_DATA')
    ios_documents = os.environ.get('IOS_DOCUMENTS_DIR')
    
    return bool(android_data_dir or ios_documents)


def get_platform_info():
    """
    獲取當前平台信息
    
    返回:
        dict: 包含平台信息的字典
    """
    return {
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'is_mobile': is_mobile_device(),
        'logs_directory': str(get_logs_directory()),
        'log_file_path': get_log_file_path(),
    }

