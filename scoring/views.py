from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, render
from .models import Room, Member, Route, Score, update_scores
from .serializers import (
    RoomSerializer, MemberSerializer, RouteSerializer,
    RouteCreateSerializer, RouteUpdateSerializer, LeaderboardSerializer, ScoreUpdateSerializer
)


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def create(self, request, *args, **kwargs):
        """創建房間"""
        data = request.data.copy()
        # 移除standard_line_score，因為它會自動計算
        if 'standard_line_score' in data:
            del data['standard_line_score']
        
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
            # 刷新 route 對象以確保 scores 關係已正確加載
            route.refresh_from_db()
            route_serializer = RouteSerializer(route, context={'request': request})
            return Response(route_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScoreViewSet(viewsets.ModelViewSet):
    queryset = Score.objects.all()
    serializer_class = ScoreUpdateSerializer

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
        import logging
        logger = logging.getLogger(__name__)
        
        route = self.get_object()
        logger.info(f"[RouteViewSet.update] 開始更新路線 ID={route.id}")
        logger.info(f"[RouteViewSet.update] 請求方法: {request.method}, Content-Type: {request.content_type}")
        
        # 處理 member_completions（如果是 JSON 字符串，轉換為字典）
        data = request.data.copy()
        logger.info(f"[RouteViewSet.update] request.data 類型: {type(request.data)}")
        logger.info(f"[RouteViewSet.update] request.data 內容: {dict(request.data) if hasattr(request.data, 'keys') else request.data}")
        
        if 'member_completions' in data:
            member_completions = data['member_completions']
            logger.info(f"[RouteViewSet.update] member_completions 原始類型: {type(member_completions)}, 值: {member_completions}")
            
            # 處理各種可能的格式
            # FormData 可能將值作為列表傳遞（QueryDict），取第一個元素
            if isinstance(member_completions, list):
                if len(member_completions) > 0:
                    member_completions = member_completions[0]
                    logger.info(f"[RouteViewSet.update] member_completions 是列表，取第一個元素: {member_completions}")
                else:
                    member_completions = '{}'
                    logger.warning(f"[RouteViewSet.update] member_completions 是空列表，設為空 JSON 字符串")
            
            # 如果已經是字典，轉換為 JSON 字符串（因為 serializer 期望字符串）
            if isinstance(member_completions, dict):
                import json
                member_completions = json.dumps(member_completions)
                logger.info(f"[RouteViewSet.update] member_completions 是字典，轉換為 JSON 字符串: {member_completions}")
            
            # 確保是字符串格式（serializer 期望 CharField）
            if not isinstance(member_completions, str):
                logger.warning(f"[RouteViewSet.update] member_completions 類型不正確 ({type(member_completions)})，轉換為字符串")
                member_completions = str(member_completions)
            
            data['member_completions'] = member_completions
            logger.info(f"[RouteViewSet.update] 最終傳遞給 serializer 的 member_completions: {member_completions} (類型: {type(member_completions)})")
        else:
            logger.warning(f"[RouteViewSet.update] request.data 中沒有 'member_completions' 字段")
            logger.info(f"[RouteViewSet.update] request.data 的所有鍵: {list(data.keys()) if hasattr(data, 'keys') else 'N/A'}")
        
        logger.info(f"[RouteViewSet.update] 傳遞給 serializer 的 data: {data}")
        
        serializer = self.get_serializer(route, data=data, partial=True, context={'request': request})
        
        if not serializer.is_valid():
            logger.error(f"[RouteViewSet.update] Serializer 驗證失敗: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info(f"[RouteViewSet.update] Serializer 驗證通過，validated_data: {serializer.validated_data}")
        serializer.save()
        
        # 重新從數據庫獲取路線，確保包含最新的 scores
        route.refresh_from_db()
        route_serializer = RouteSerializer(route, context={'request': request})
        logger.info(f"[RouteViewSet.update] 更新完成，返回的 scores 數量: {len(route_serializer.data.get('scores', []))}")
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

    def update(self, request, *args, **kwargs):
        """更新成員"""
        member = self.get_object()
        serializer = self.get_serializer(member, data=request.data, partial=True)
        
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


def index_view(request):
    """首頁視圖"""
    return render(request, 'index.html')


def leaderboard_view(request, room_id):
    """排行榜頁面視圖"""
    return render(request, 'leaderboard.html', {'room_id': room_id})


def rules_view(request):
    """說明頁面視圖"""
    return render(request, 'rules.html')

