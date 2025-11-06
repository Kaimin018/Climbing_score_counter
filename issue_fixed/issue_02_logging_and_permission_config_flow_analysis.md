# 日誌配置和權限配置問題流程分析

## 問題 1: 日誌配置流程分析

### 問題觸發流程

```
1. Django 啟動
   ↓
2. 加載 settings.py
   ↓
3. 配置 LOGGING
   ↓
4. 嘗試創建 file handler
   ↓
5. 檢查 logs/django.log 文件
   ↓
6. logs/ 目錄不存在 ❌
   ↓
7. FileNotFoundError
   ↓
8. 日誌配置失敗
   ↓
9. Django 無法啟動
```

### 修復後流程

```
1. Django 啟動
   ↓
2. 加載 settings.py
   ↓
3. 配置基礎 LOGGING（只有 console handler）
   ↓
4. 檢查 DEBUG 設置
   ↓
5. 如果 DEBUG=False（生產環境）
   ├─ 創建 logs/ 目錄（如果不存在）
   ├─ 添加 file handler
   └─ 將 file handler 添加到 loggers
   ↓
6. 如果 DEBUG=True（開發環境）
   └─ 只使用 console handler
   ↓
7. 日誌配置成功 ✅
   ↓
8. Django 正常啟動
```

### 代碼執行路徑

**開發環境 (DEBUG=True)**:
```python
LOGGING = {
    'handlers': {'console': {...}},  # 只有 console
    'loggers': {
        'scoring': {'handlers': ['console']},  # 只使用 console
    },
}
# if not DEBUG:  # 不執行
```

**生產環境 (DEBUG=False)**:
```python
LOGGING = {
    'handlers': {'console': {...}},
    'loggers': {
        'scoring': {'handlers': ['console']},
    },
}
if not DEBUG:  # 執行
    logs_dir.mkdir(exist_ok=True)  # 創建目錄
    LOGGING['handlers']['file'] = {...}  # 添加 file handler
    LOGGING['loggers']['scoring']['handlers'].append('file')  # 添加文件日誌
```

## 問題 2: 權限配置流程分析

### 問題觸發流程

```
1. 測試發送 POST /api/rooms/
   ↓
2. 請求到達 RoomViewSet.create()
   ↓
3. DRF 檢查權限
   ↓
4. 使用 IsAuthenticatedOrReadOnlyForCreate
   ↓
5. 檢查 request.user.is_authenticated
   ↓
6. 測試未提供認證信息
   ↓
7. is_authenticated = False ❌
   ↓
8. 權限檢查失敗
   ↓
9. 返回 403 Forbidden
```

### 修復後流程（開發環境）

```
1. 測試發送 POST /api/rooms/
   ↓
2. 請求到達 RoomViewSet.create()
   ↓
3. DRF 檢查權限
   ↓
4. 使用 DEFAULT_PERMISSION_CLASSES
   ↓
5. DEBUG=True → 使用 AllowAny
   ↓
6. AllowAny.has_permission() 返回 True ✅
   ↓
7. 權限檢查通過
   ↓
8. 執行 create() 方法
   ↓
9. 返回 201 Created
```

### 修復後流程（生產環境）

```
1. 用戶發送 POST /api/rooms/
   ↓
2. 請求到達 RoomViewSet.create()
   ↓
3. DRF 檢查權限
   ↓
4. 使用 DEFAULT_PERMISSION_CLASSES
   ↓
5. DEBUG=False → 使用 IsAuthenticatedOrReadOnly
   ↓
6. 檢查 request.method
   ↓
7. POST 不是安全方法
   ↓
8. 檢查 request.user.is_authenticated
   ↓
9. 如果已認證 ✅ → 允許
   如果未認證 ❌ → 返回 403
```

### 權限檢查決策樹

```
請求到達 ViewSet
    ↓
檢查 permission_classes
    ↓
如果設置了 permission_classes
    → 使用 ViewSet 的權限類
否則
    → 使用 DEFAULT_PERMISSION_CLASSES
        ↓
    檢查 DEBUG
        ↓
    如果 DEBUG=True
        → AllowAny → 允許所有操作 ✅
    如果 DEBUG=False
        → IsAuthenticatedOrReadOnly
            ↓
        檢查 HTTP 方法
            ↓
        如果是安全方法 (GET, HEAD, OPTIONS)
            → 允許 ✅
        如果不是安全方法
            → 檢查認證
                ↓
            如果已認證
                → 允許 ✅
            如果未認證
                → 拒絕 ❌ (403)
```

## 配置加載順序

### Django 設置加載

```
1. 加載 settings.py
   ↓
2. 讀取環境變數
   SECRET_KEY = os.environ.get('SECRET_KEY', '...')
   DEBUG = os.environ.get('DEBUG', 'True') == 'True'
   ↓
3. 配置 REST_FRAMEWORK
   DEFAULT_PERMISSION_CLASSES = (
       ['AllowAny'] if DEBUG 
       else ['IsAuthenticatedOrReadOnly']
   )
   ↓
4. 配置 LOGGING（基礎配置）
   ↓
5. 如果 DEBUG=False
   → 添加文件日誌配置
   ↓
6. 配置完成
```

### ViewSet 權限解析

```
1. 請求到達 ViewSet
   ↓
2. DRF 調用 get_permissions()
   ↓
3. 檢查 permission_classes 屬性
   ↓
4. 如果設置了 permission_classes
   → 使用該權限類
   ↓
5. 如果未設置 permission_classes
   → 使用 DEFAULT_PERMISSION_CLASSES
   ↓
6. 實例化權限類
   ↓
7. 調用 has_permission()
   ↓
8. 返回權限檢查結果
```

## 測試執行流程

### 測試環境設置

```
1. Django TestCase.setUp()
   ↓
2. 創建測試數據庫
   ↓
3. 加載 settings.py
   ↓
4. DEBUG=True（測試環境默認）
   ↓
5. REST_FRAMEWORK 使用 AllowAny
   ↓
6. LOGGING 只使用 console handler
   ↓
7. 測試開始執行
```

### 測試請求流程

```
1. test_create_route()
   ↓
2. self.client.post('/api/rooms/1/routes/', ...)
   ↓
3. APIClient 發送 HTTP 請求
   ↓
4. Django URL 路由
   ↓
5. RoomViewSet.create_route()
   ↓
6. DRF 權限檢查
   ↓
7. AllowAny.has_permission() → True ✅
   ↓
8. 執行 create_route() 方法
   ↓
9. 返回 Response(201)
   ↓
10. 測試驗證 response.status_code == 201 ✅
```

## 生產環境部署流程

### 環境變數設置

```bash
export DEBUG=False
export SECRET_KEY=your-production-secret-key
export ALLOWED_HOSTS=your-domain.com
```

### 配置生效流程

```
1. 設置環境變數
   ↓
2. 啟動 Gunicorn
   ↓
3. Django 加載 settings.py
   ↓
4. 讀取環境變數
   DEBUG = os.environ.get('DEBUG', 'True') == 'True'
   → DEBUG = False ✅
   ↓
5. REST_FRAMEWORK 配置
   DEFAULT_PERMISSION_CLASSES = ['IsAuthenticatedOrReadOnly'] ✅
   ↓
6. LOGGING 配置
   if not DEBUG:  # 執行
   → 創建 logs/ 目錄
   → 添加 file handler ✅
   ↓
7. 應用啟動完成
   ↓
8. 所有 API 請求需要認證 ✅
```

## 關鍵決策點

### 決策點 1: 日誌配置時機

**選擇**: 在 `settings.py` 加載時動態配置

**原因**:
- 避免在開發環境創建不必要的文件
- 確保生產環境有完整的日誌功能
- 自動創建目錄，減少部署步驟

### 決策點 2: 權限配置方式

**選擇**: 使用 `DEFAULT_PERMISSION_CLASSES` 而不是 ViewSet 級別設置

**原因**:
- 統一管理權限配置
- 根據環境自動切換
- 減少代碼重複

### 決策點 3: 測試策略

**選擇**: 測試根據環境調整預期行為

**原因**:
- 開發環境允許所有操作，便於測試
- 生產環境需要認證，保證安全
- 測試需要驗證兩種環境的行為

## 潛在問題和解決方案

### 問題 1: 日誌目錄權限

**問題**: 生產環境可能沒有寫入權限

**解決方案**: 
- 在部署腳本中設置目錄權限
- 使用 systemd 服務文件設置正確的用戶和組

### 問題 2: 環境變數未設置

**問題**: 生產環境忘記設置 `DEBUG=False`

**解決方案**:
- 在部署文檔中明確說明
- 在啟動腳本中檢查環境變數
- 添加健康檢查

### 問題 3: 權限配置緩存

**問題**: Django 設置可能被緩存

**解決方案**:
- 使用環境變數動態配置
- 重啟服務使配置生效
- 在測試中使用 `override_settings`

