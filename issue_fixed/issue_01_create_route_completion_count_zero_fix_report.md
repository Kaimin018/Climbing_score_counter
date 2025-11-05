# 工程報告：創建路線時完成人數顯示為 0 的問題修復

## 問題描述

**症狀**: 在既有房間中創建新路線時，即使建立當下就勾選了多個完成成員，路線列表顯示的完成人數仍然是 0，而不是正確的完成人數。

**影響範圍**: 所有使用者在創建路線時無法看到正確的完成人數統計。

## 問題根源

### 核心問題

`RouteCreateSerializer` 序列化器中的 `member_completions` 字段使用了 `DictField` 類型。當視圖層收到前端的 FormData（包含 JSON 字符串）後，如果將 JSON 字符串解析為字典再傳給序列化器，`DictField` 無法正確處理這個字典，導致 `member_completions` 變成空字典 `{}`。

### 問題流程

1. 前端提交 FormData，`member_completions` 是 JSON 字符串：`'{"3": true, "4": true}'`
2. 視圖層解析 JSON 字符串為字典：`{'3': True, '4': True}`
3. 序列化器的 `DictField` 無法正確處理已解析的字典，導致 `validated_data['member_completions']` 變成 `{}`
4. 創建 Score 記錄時，所有成員的 `is_completed` 都被設為 `False`
5. 前端顯示時，完成人數為 0

## 修復方案

### 1. 修改序列化器字段類型

**修改前**:
```python
member_completions = serializers.DictField(
    child=serializers.BooleanField(),
    write_only=True
)
```

**修改後**:
```python
member_completions = serializers.CharField(
    write_only=True,
    required=False,
    allow_blank=True
)
```

### 2. 添加驗證方法統一處理

在 `RouteCreateSerializer` 中添加 `validate_member_completions` 方法，統一處理 JSON 字符串解析：

```python
def validate_member_completions(self, value):
    """驗證並解析 member_completions"""
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return {}
    
    # 如果是字符串，解析 JSON
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    
    # 如果已經是字典，直接返回
    return value if isinstance(value, dict) else {}
```

### 3. 改進視圖層處理邏輯

在 `RoomViewSet.create_route` 中，確保 FormData 中的 JSON 字符串保持為字符串格式，讓序列化器統一處理：

```python
# 如果已經是字典（可能來自測試場景），轉換回 JSON 字符串
if isinstance(member_completions_value, dict):
    data['member_completions'] = json.dumps(member_completions_value)
```

### 4. 改進數據預取

在 `RoomViewSet.retrieve()` 和 `get_queryset()` 中使用 `prefetch_related` 預取相關數據，確保數據完整：

```python
def get_queryset(self):
    return Room.objects.prefetch_related(
        'routes__scores__member',
        'members'
    ).all()
```

## 修復效果

### 修復前
- 創建路線時，即使勾選完成成員，所有 Score 的 `is_completed` 都是 `False`
- 前端顯示完成人數為 0

### 修復後
- 創建路線時，正確根據 `member_completions` 設置每個成員的 `is_completed`
- 前端正確顯示完成人數（例如：完成: 2/3 人）

## 測試驗證

### 新增測試案例

添加了深度測試 `test_create_route_deep_dive_complete_flow`，完整驗證：

1. ✅ 創建路線時正確處理 `member_completions`
2. ✅ Score 記錄正確創建並設置 `is_completed`
3. ✅ 創建響應中的 `scores` 數據正確
4. ✅ 立即獲取房間數據時，`scores` 數據正確
5. ✅ 前端計算邏輯正確（完成人數統計）
6. ✅ 數據庫一致性（API 數據與數據庫數據一致）

### 測試結果

- ✅ 所有 27 個測試通過
- ✅ 無回歸問題
- ✅ 修復驗證通過

## 技術要點

### 1. FormData 與 JSON 處理

前端使用 `FormData` 提交數據時，JSON 對象需要先轉換為字符串：
```javascript
formData.append('member_completions', JSON.stringify(memberCompletions));
```

後端序列化器需要統一處理 JSON 字符串解析，避免在不同層級重複解析。

### 2. Django REST Framework 序列化器

- `DictField` 適合處理直接傳入的字典數據
- `CharField` + 自定義驗證方法更適合處理 JSON 字符串
- 統一在序列化器層級處理數據轉換，避免視圖層過度處理

### 3. 數據預取優化

使用 `prefetch_related` 預取相關數據，避免 N+1 查詢問題，同時確保數據完整性。

## 相關文件

- 詳細流程分析：`issue_fixed/FLOW_ANALYSIS.md`
- 修復的代碼：
  - `scoring/serializers.py` - `RouteCreateSerializer`
  - `scoring/views.py` - `RoomViewSet.create_route` 和 `retrieve`
- 測試案例：`scoring/tests/test_api.py` - `test_create_route_deep_dive_complete_flow`

## 總結

此問題源於序列化器字段類型選擇不當，導致無法正確處理 FormData 中的 JSON 數據。通過將字段類型改為 `CharField` 並添加統一的驗證方法，成功解決了數據解析問題，確保創建路線時能正確設置成員完成狀態，前端也能正確顯示完成人數。

