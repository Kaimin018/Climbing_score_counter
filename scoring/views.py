from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import Room, Member, Route, Score, update_scores
from .serializers import (
    RoomSerializer, MemberSerializer, RouteSerializer,
    RouteCreateSerializer, RouteUpdateSerializer, LeaderboardSerializer, ScoreUpdateSerializer
)
from .permissions import IsAuthenticatedOrReadOnlyForCreate


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    # 使用 settings.py 中的默認權限設置（開發環境為 AllowAny）
    
    def get_queryset(self):
        """確保查詢時預加載相關數據"""
        return Room.objects.prefetch_related(
            'routes__scores__member',
            'members'
        ).all()
    
    def retrieve(self, request, *args, **kwargs):
        """獲取房間詳情，確保數據最新"""
        instance = self.get_object()
        
        # 強制清除可能的緩存，重新查詢並預取相關數據
        instance.refresh_from_db()
        instance = Room.objects.prefetch_related(
            'routes__scores__member',
            'members'
        ).get(pk=instance.pk)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """創建房間"""
        data = request.data.copy()
        # 移除standard_line_score，因為它會自動計算
        if 'standard_line_score' in data:
            del data['standard_line_score']
        
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            room = serializer.save()
            # 創建房間後自動計算standard_line_score
            # 注意：如果房間剛創建還沒有成員，會使用默認值12
            update_scores(room.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """更新房間"""
        room = self.get_object()
        # 移除standard_line_score，因為它會自動計算
        data = request.data.copy()
        if 'standard_line_score' in data:
            del data['standard_line_score']
        
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        
        serializer = self.get_serializer(room, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # 更新後自動重新計算分數（會自動更新standard_line_score）
            update_scores(room.id)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request, pk=None):
        """獲取排行榜"""
        room = self.get_object()
        
        # 按總分降序排序
        members = room.members.all().order_by('-total_score', 'name')
        
        room_info = {
            'name': room.name,
            'standard_line_score': room.standard_line_score,
            'id': room.id
        }
        
        serializer = LeaderboardSerializer({
            'room_info': room_info,
            'leaderboard': members
        })
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='routes')
    def create_route(self, request, pk=None):
        """新增路線與成績錄入"""
        room = self.get_object()
        
        # 處理 member_completions：FormData 中的 JSON 字符串應該保持為字符串，讓序列化器處理
        # 如果已經是字典（可能來自測試場景），轉換回 JSON 字符串
        data = request.data.copy()
        if 'member_completions' in data and isinstance(data['member_completions'], dict):
            import json
            data['member_completions'] = json.dumps(data['member_completions'])
        
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        if 'grade' in data:
            data['grade'] = escape(data['grade'])
        
        serializer = RouteCreateSerializer(data=data, context={'room': room, 'request': request})
        if serializer.is_valid():
            route = serializer.save()
            
            # 強制從數據庫重新獲取 route 對象，確保 scores 關係已正確加載
            from .models import Route
            route = Route.objects.prefetch_related('scores__member').get(id=route.id)
            
            route_serializer = RouteSerializer(route, context={'request': request})
            return Response(route_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.all()
    serializer_class = ScoreUpdateSerializer
    # 使用 settings.py 中的默認權限設置（開發環境為 AllowAny）

    def update(self, request, *args, **kwargs):
        """更新成績狀態（標記完成/未完成）"""
        score = self.get_object()
        serializer = self.get_serializer(score, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # 觸發計分更新
            update_scores(score.member.room.id)
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.all()
    # 使用 settings.py 中的默認權限設置（開發環境為 AllowAny）
    
    def get_serializer_class(self):
        """根據操作選擇不同的序列化器"""
        if self.action == 'create':
            return RouteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RouteUpdateSerializer
        return RouteSerializer
    
    def get_serializer_context(self):
        """為序列化器提供上下文"""
        context = super().get_serializer_context()
        context['request'] = self.request
        if self.action == 'create':
            # 從請求路徑中獲取房間ID（如果路徑是 /api/rooms/{room_id}/routes/）
            room_id = self.request.parser_context['kwargs'].get('room_pk')
            if room_id:
                from .models import Room
                try:
                    context['room'] = Room.objects.get(id=room_id)
                except Room.DoesNotExist:
                    pass
        return context
    
    def retrieve(self, request, *args, **kwargs):
        """獲取路線詳情"""
        route = self.get_object()
        serializer = RouteSerializer(route, context={'request': request})
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """更新路線"""
        route = self.get_object()
        data = request.data.copy()
        
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        if 'grade' in data:
            data['grade'] = escape(data['grade'])
        
        # 處理 member_completions：FormData 可能將值作為列表傳遞（QueryDict），取第一個元素
        # 如果已經是字典，轉換為 JSON 字符串（因為 serializer 期望字符串）
        if 'member_completions' in data:
            member_completions = data['member_completions']
            if isinstance(member_completions, list):
                member_completions = member_completions[0] if len(member_completions) > 0 else '{}'
            if isinstance(member_completions, dict):
                import json
                member_completions = json.dumps(member_completions)
            if not isinstance(member_completions, str):
                member_completions = str(member_completions)
            data['member_completions'] = member_completions
        
        serializer = self.get_serializer(route, data=data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        
        # 重新從數據庫獲取路線，確保包含最新的 scores
        route.refresh_from_db()
        route_serializer = RouteSerializer(route, context={'request': request})
        return Response(route_serializer.data)

    def destroy(self, request, *args, **kwargs):
        """刪除路線"""
        route = self.get_object()
        room_id = route.room.id
        
        # 刪除路線（會級聯刪除相關的 Score 記錄）
        route.delete()
        
        # 觸發計分更新
        update_scores(room_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    # 使用 settings.py 中的默認權限設置（開發環境為 AllowAny）

    def create(self, request, *args, **kwargs):
        """創建成員"""
        data = request.data.copy()
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            member = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        """更新成員"""
        member = self.get_object()
        data = request.data.copy()
        # 清理用戶輸入，防止 XSS
        if 'name' in data:
            data['name'] = escape(data['name'])
        serializer = self.get_serializer(member, data=data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            # 更新後自動重新計算分數（會自動更新standard_line_score）
            update_scores(member.room.id)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """刪除成員"""
        member = self.get_object()
        room_id = member.room.id
        
        # 刪除成員（會級聯刪除相關的 Score 記錄）
        member.delete()
        
        # 觸發計分更新（會自動更新standard_line_score）
        update_scores(room_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['get'], url_path='completed-routes')
    def completed_routes(self, request, pk=None):
        """獲取成員完成的路線列表"""
        member = self.get_object()
        
        # 獲取該成員所有完成的路線
        completed_scores = member.scores.filter(is_completed=True).select_related('route')
        routes = [score.route for score in completed_scores]
        
        # 使用 RouteSerializer 序列化路線
        from .serializers import RouteSerializer
        route_serializer = RouteSerializer(routes, many=True, context={'request': request})
        
        return Response({
            'member_id': member.id,
            'member_name': member.name,
            'completed_routes': route_serializer.data,
            'total_count': len(routes)
        })


@ensure_csrf_cookie
def index_view(request):
    """首頁視圖 - 未登錄顯示登錄界面，已登錄顯示房間列表"""
    return render(request, 'index.html', {
        'user': request.user if request.user.is_authenticated else None
    })


@ensure_csrf_cookie
def leaderboard_view(request, room_id):
    """排行榜頁面視圖"""
    return render(request, 'leaderboard.html', {'room_id': room_id})


@ensure_csrf_cookie
def rules_view(request):
    """說明頁面視圖"""
    return render(request, 'rules.html')

