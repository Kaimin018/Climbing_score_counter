# 新增路線流程分析

## 完整流程追蹤

### 1. 前端：點擊「新增路線」按鈕

**位置**: `templates/leaderboard.html` 第 1022 行

```javascript
document.getElementById('addRouteForm').addEventListener('submit', function(e) {
    // 收集成員完成狀態
    const checkboxes = document.querySelectorAll('#memberCompletions input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        memberCompletions[checkbox.value] = checkbox.checked;
    });
    
    // 構建 FormData
    formData.append('member_completions', JSON.stringify(memberCompletions));
    
    // 發送 POST 請求
    fetch(`/api/rooms/${ROOM_ID}/routes/`, {
        method: 'POST',
        body: formData
    })
```

**關鍵點**:
- `memberCompletions` 是一個對象，格式為 `{ "member_id": true/false }`
- `checkbox.value` 是成員 ID（字符串）
- 使用 `JSON.stringify()` 轉換為字符串後放入 FormData

---

### 2. 後端：接收請求 (RoomViewSet.create_route)

**位置**: `scoring/views.py` 第 91-115 行

```python
@action(detail=True, methods=['post'], url_path='routes')
def create_route(self, request, pk=None):
    room = self.get_object()
    
    # 處理 member_completions（如果是 JSON 字符串，轉換為字典）
    data = request.data.copy()
    if 'member_completions' in data and isinstance(data['member_completions'], str):
        import json
        try:
            data['member_completions'] = json.loads(data['member_completions'])
        except json.JSONDecodeError:
            data['member_completions'] = {}
    
    serializer = RouteCreateSerializer(data=data, context={'room': room, 'request': request})
    if serializer.is_valid():
        route = serializer.save()
        # 強制從數據庫重新獲取 route 對象
        route = Route.objects.prefetch_related('scores__member').get(id=route.id)
        route_serializer = RouteSerializer(route, context={'request': request})
        return Response(route_serializer.data, status=status.HTTP_201_CREATED)
```

**關鍵點**:
- FormData 中的 `member_completions` 是 JSON 字符串，需要解析
- 創建路線後，使用 `prefetch_related` 重新查詢以確保 scores 關係正確加載

---

### 3. 後端：序列化器處理 (RouteCreateSerializer.create)

**位置**: `scoring/serializers.py` 第 57-86 行

```python
def create(self, validated_data):
    member_completions = validated_data.pop('member_completions', {})
    room = self.context['room']
    
    # 處理 member_completions（可能是 JSON 字符串）
    if isinstance(member_completions, str):
        import json
        try:
            member_completions = json.loads(member_completions)
        except json.JSONDecodeError:
            member_completions = {}
    
    # 創建路線
    route = Route.objects.create(room=room, **validated_data)
    
    # 批量創建所有成員的 Score 記錄
    members = room.members.all()
    for member in members:
        is_completed = member_completions.get(str(member.id), False)
        Score.objects.create(
            member=member,
            route=route,
            is_completed=is_completed
        )
    
    # 觸發計分更新
    update_scores(room.id)
    
    return route
```

**關鍵點**:
- `member_completions.get(str(member.id), False)` - 使用字符串形式的 member.id 作為 key
- 為所有成員創建 Score 記錄（已完成和未完成的）
- 調用 `update_scores()` 更新分數

---

### 4. 後端：返回響應 (RouteSerializer)

**位置**: `scoring/serializers.py` 第 14-28 行

```python
class RouteSerializer(serializers.ModelSerializer):
    scores = ScoreSerializer(many=True, read_only=True)
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # 從數據庫重新獲取 scores 以確保數據最新
        scores = instance.scores.all()
        representation['scores'] = ScoreSerializer(scores, many=True).data
        return representation
```

**關鍵點**:
- 使用 `instance.scores.all()` 重新查詢 scores，確保數據最新
- 返回的 `scores` 是一個數組，每個元素包含 `is_completed` 字段

---

### 5. 前端：接收創建響應

**位置**: `templates/leaderboard.html` 第 1062-1066 行

```javascript
.then(response => response.json())
.then(data => {
    if (data.id) {
        closeAddRouteModal();
        refreshLeaderboard();  // 立即刷新
        alert('路線創建成功！');
    }
})
```

**關鍵點**:
- 創建成功後立即調用 `refreshLeaderboard()`
- **注意**: 前端沒有使用創建響應中的 `data.scores`，而是通過 `refreshLeaderboard()` 重新獲取

---

### 6. 前端：刷新排行榜 (refreshLeaderboard)

**位置**: `templates/leaderboard.html` 第 403-408 行

```javascript
function refreshLeaderboard() {
    // 先重新載入路線列表，確保數據同步
    loadRoutes();
    // 然後載入排行榜
    loadLeaderboard();
}
```

---

### 7. 前端：載入路線列表 (loadRoutes)

**位置**: `templates/leaderboard.html` 第 410-421 行

```javascript
function loadRoutes() {
    fetch(`/api/rooms/${ROOM_ID}/`)
        .then(response => response.json())
        .then(data => {
            displayRoutes(data.routes || []);
        })
}
```

**關鍵點**:
- 通過 `GET /api/rooms/{id}/` 獲取房間數據
- 這會調用 `RoomViewSet.retrieve()` 方法

---

### 8. 後端：獲取房間詳情 (RoomViewSet.retrieve)

**位置**: `scoring/views.py` 第 23-34 行

```python
def retrieve(self, request, *args, **kwargs):
    instance = self.get_object()
    # 強制清除可能的緩存，重新查詢並預取
    instance.refresh_from_db()
    # 重新獲取並預取相關數據
    instance = Room.objects.prefetch_related(
        'routes__scores__member',
        'members'
    ).get(pk=instance.pk)
    serializer = self.get_serializer(instance)
    return Response(serializer.data)
```

**關鍵點**:
- 使用 `prefetch_related('routes__scores__member')` 預取所有相關數據
- 調用 `RoomSerializer` 序列化房間數據

---

### 9. 後端：序列化房間 (RoomSerializer.to_representation)

**位置**: `scoring/serializers.py` 第 309-330 行

```python
def to_representation(self, instance):
    representation = super().to_representation(instance)
    request = self.context.get('request')
    
    # 如果已經預取，使用預取的數據；否則重新查詢
    if hasattr(instance, '_prefetched_objects_cache') and 'routes' in instance._prefetched_objects_cache:
        routes = instance._prefetched_objects_cache['routes']
    else:
        routes = instance.routes.prefetch_related('scores__member').all()
    
    representation['routes'] = RouteSerializer(
        routes, 
        many=True, 
        context={'request': request} if request else {}
    ).data
    return representation
```

**關鍵點**:
- 檢查是否有預取緩存，如果有則使用，否則重新查詢
- 對每個 route 調用 `RouteSerializer` 序列化

---

### 10. 前端：顯示路線 (displayRoutes)

**位置**: `templates/leaderboard.html` 第 423-460 行

```javascript
function displayRoutes(routes) {
    container.innerHTML = routes.map(route => {
        // 統計完成人數
        const completedCount = route.scores ? route.scores.filter(s => s.is_completed).length : 0;
        const totalCount = route.scores ? route.scores.length : 0;
        
        return `
            <div class="route-stats">
                完成: ${completedCount}/${totalCount} 人
            </div>
        `;
    }).join('');
}
```

**關鍵點**:
- `route.scores` 應該是一個數組
- 使用 `filter(s => s.is_completed)` 統計完成人數
- **問題可能出現在這裡**: 如果 `route.scores` 為 `undefined` 或 `null`，則 `completedCount` 會是 0

---

## 已修復的問題

1. **序列化器字段類型問題**:
   - **問題**: `RouteCreateSerializer.member_completions` 使用 `DictField`，當視圖中解析 JSON 後傳入字典時，序列化器無法正確處理
   - **修復**: 改為 `CharField`，添加 `validate_member_completions` 方法統一處理 JSON 字符串解析

2. **數據預取問題**:
   - **問題**: 創建路線後立即獲取房間數據時，scores 關係可能未正確加載
   - **修復**: 在 `RoomViewSet.get_queryset()` 和 `retrieve()` 中使用 `prefetch_related` 預取相關數據

3. **緩存問題**:
   - **問題**: Django ORM 的預取緩存可能沒有正確更新
   - **修復**: 在 `RouteSerializer.to_representation` 中智能處理預取緩存，如果沒有預取則重新查詢

## 關鍵修復點

### 1. RouteCreateSerializer.member_completions 字段類型

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

### 2. 添加 validate_member_completions 方法

統一處理 JSON 字符串解析，支持字符串和字典兩種格式。

### 3. RouteCreateSerializer.create 方法

改進 member_completions 的查找邏輯，支持字符串和整數兩種 key 格式。

## 測試驗證

已添加深度測試 `test_create_route_deep_dive_complete_flow`，驗證：
1. 創建路線時正確處理 member_completions
2. Score 記錄正確創建並設置 is_completed
3. 創建響應中的 scores 數據正確
4. 立即獲取房間數據時，scores 數據正確
5. 前端計算邏輯正確
6. 數據庫一致性

