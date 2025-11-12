# 生產環境測試指南

本指南說明如何在生產環境模式下測試系統，特別是測試訪客權限限制功能。

## 方法一：使用環境變數（推薦）

### Windows PowerShell

```powershell
# 設置生產環境變數
$env:DEBUG = "False"
$env:SECRET_KEY = "your-secret-key-here"

# 運行測試（測試會自動使用 override_settings，無需手動設置）
python manage.py test scoring.tests.test_case_34_guest_permission_restrictions

# 或啟動開發服務器（生產模式）
python manage.py runserver
```

**注意**：測試文件已經使用了 `@override_settings` 裝飾器，會自動模擬生產環境，所以即使不設置環境變數，測試也會正確運行。

### Windows CMD

```cmd
# 設置生產環境變數
set DEBUG=False
set SECRET_KEY=your-secret-key-here

# 運行測試
python manage.py test scoring.tests.test_case_34_guest_permission_restrictions

# 或啟動開發服務器（生產模式）
python manage.py runserver
```

### Linux/macOS

```bash
# 設置生產環境變數
export DEBUG=False
export SECRET_KEY=your-secret-key-here

# 運行測試
python manage.py test scoring.tests.test_case_34_guest_permission_restrictions

# 或啟動開發服務器（生產模式）
python manage.py runserver
```

## 方法二：使用測試裝飾器（已在測試中使用）

測試文件 `test_case_34_guest_permission_restrictions.py` 已經使用了 `@override_settings` 裝飾器來模擬生產環境：

```python
@override_settings(
    DEBUG=False,
    REST_FRAMEWORK={
        'DEFAULT_PERMISSION_CLASSES': ['scoring.permissions.IsMemberOrReadOnly']
    }
)
def test_guest_cannot_create_room(self):
    # 測試代碼
```

直接運行測試即可：

```bash
python manage.py test scoring.tests.test_case_34_guest_permission_restrictions
```

## 方法三：手動測試（瀏覽器/API 工具）

### 1. 啟動生產模式服務器

```powershell
# Windows PowerShell
$env:DEBUG = "False"
python manage.py runserver
```

### 2. 測試訪客權限

#### 測試訪客登錄
```bash
# 使用 curl 或 Postman
POST http://localhost:8000/api/auth/guest-login/
```

#### 測試訪客讀取（應該成功）
```bash
GET http://localhost:8000/api/rooms/
```

#### 測試訪客創建（應該失敗，返回 403）
```bash
POST http://localhost:8000/api/rooms/
Content-Type: application/json
{
  "name": "訪客創建的房間"
}
```

#### 測試普通用戶創建（應該成功）
```bash
# 1. 先註冊/登錄普通用戶
POST http://localhost:8000/api/auth/register/
Content-Type: application/json
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "TestPass123!",
  "password_confirm": "TestPass123!"
}

# 2. 使用登錄後的 session 創建房間
POST http://localhost:8000/api/rooms/
Content-Type: application/json
Cookie: sessionid=...
{
  "name": "普通用戶創建的房間"
}
```

## 驗證生產環境配置

### 檢查當前 DEBUG 狀態

```python
# 在 Django shell 中檢查
python manage.py shell

>>> from django.conf import settings
>>> print(f"DEBUG: {settings.DEBUG}")
>>> print(f"Permission Classes: {settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']}")
```

### 檢查權限類

```python
# 在 Django shell 中檢查
python manage.py shell

>>> from scoring.permissions import IsMemberOrReadOnly
>>> from django.contrib.auth.models import User
>>> 
>>> # 創建測試用戶
>>> guest = User.objects.create_user(username='guest_test', password='dummy')
>>> regular = User.objects.create_user(username='regular_test', password='dummy')
>>> 
>>> # 測試權限類
>>> from rest_framework.test import APIRequestFactory
>>> from rest_framework.request import Request
>>> 
>>> factory = APIRequestFactory()
>>> request = factory.post('/api/rooms/', {'name': 'test'})
>>> request.user = guest
>>> 
>>> permission = IsMemberOrReadOnly()
>>> print(f"訪客 POST 權限: {permission.has_permission(Request(request), None)}")  # 應該是 False
>>> 
>>> request.user = regular
>>> print(f"普通用戶 POST 權限: {permission.has_permission(Request(request), None)}")  # 應該是 True
```

## 快速測試腳本

已經創建了快速測試腳本 `test_production_permission.py`，可以直接運行：

```powershell
# Windows PowerShell
# 注意：腳本內部已經自動設置 DEBUG=False，所以不需要手動設置環境變數
python test_production_permission.py
```

```bash
# Linux/macOS
python test_production_permission.py
```

### 這個腳本的作用

這個腳本**只測試權限類是否正常工作**，運行完就結束了，**不會啟動服務器**。

它會：
1. 自動設置 `DEBUG=False`（腳本內部處理）
2. 創建測試用戶（訪客和普通用戶）
3. 測試權限類的行為
4. 驗證訪客只能讀取，普通用戶可以讀寫
5. 顯示測試結果並退出

**預期輸出**：
```
============================================================
Production Permission Test
============================================================
DEBUG: False
Permission Classes: ['scoring.permissions.IsMemberOrReadOnly']

Guest POST permission: False (should be False)
Regular user POST permission: True (should be True)
Guest GET permission: True (should be True)

============================================================
Test Results
============================================================
SUCCESS: All tests passed!
```

### 如果想要啟動服務器進行實際測試

如果您想要啟動服務器，在瀏覽器或 API 工具中實際測試訪客權限，需要**另外啟動服務器**：

```powershell
# Windows PowerShell
# 在同一個 PowerShell 會話中設置環境變數（因為腳本不會保留環境變數）
$env:DEBUG = "False"
python manage.py runserver
```

**重要提示**：
- `test_production_permission.py` 只是驗證權限邏輯，不會啟動服務器
- 如果要在瀏覽器中測試，需要單獨運行 `python manage.py runserver`
- 環境變數 `$env:DEBUG = "False"` 只在當前 PowerShell 會話中有效
- 如果關閉 PowerShell 窗口，需要重新設置環境變數

## 手動測試腳本（舊版，已棄用）

如果您想創建自己的測試腳本，可以參考以下代碼：

```python
#!/usr/bin/env python
"""
快速測試生產環境模式
"""
import os
import sys
import django

# 設置生產環境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climbing_system.settings')
os.environ['DEBUG'] = 'False'

django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from scoring.permissions import IsMemberOrReadOnly

print("=" * 50)
print("生產環境配置檢查")
print("=" * 50)
print(f"DEBUG: {settings.DEBUG}")
print(f"Permission Classes: {settings.REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']}")
print()

# 測試權限
factory = APIRequestFactory()
permission = IsMemberOrReadOnly()

# 測試訪客用戶
guest = User.objects.create_user(username='guest_test_prod', password='dummy')
request = factory.post('/api/rooms/', {'name': 'test'})
request.user = guest
guest_permission = permission.has_permission(Request(request), None)
print(f"訪客 POST 權限: {guest_permission} (應該是 False)")

# 測試普通用戶
regular = User.objects.create_user(username='regular_test_prod', password='dummy')
request.user = regular
regular_permission = permission.has_permission(Request(request), None)
print(f"普通用戶 POST 權限: {regular_permission} (應該是 True)")

# 測試讀取權限（訪客應該可以）
request = factory.get('/api/rooms/')
request.user = guest
guest_read_permission = permission.has_permission(Request(request), None)
print(f"訪客 GET 權限: {guest_read_permission} (應該是 True)")

print()
print("=" * 50)
print("測試結果")
print("=" * 50)
if not guest_permission and regular_permission and guest_read_permission:
    print("✅ 所有測試通過！")
else:
    print("❌ 測試失敗，請檢查配置")

# 清理
guest.delete()
regular.delete()
```

運行腳本：

```bash
python test_production_mode.py
```

## 注意事項

1. **環境變數持久性**：
   - PowerShell/CMD 中設置的環境變數只在當前會話有效
   - 關閉終端後需要重新設置

2. **測試數據庫**：
   - Django 測試會自動創建測試數據庫
   - 不會影響實際的 `db.sqlite3` 文件

3. **權限緩存**：
   - 如果修改了權限配置，需要重啟服務器
   - 測試中使用 `@override_settings` 會自動處理

4. **生產環境部署**：
   - 實際部署時，建議使用 `.env` 文件或系統環境變數
   - 參考 `env.example` 文件配置

## 相關文件

- `scoring/permissions.py` - 權限類定義
- `climbing_system/settings.py` - 權限配置
- `scoring/tests/test_case_34_guest_permission_restrictions.py` - 測試用例
- `env.example` - 環境變數範例

