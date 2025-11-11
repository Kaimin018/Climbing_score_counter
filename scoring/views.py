from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, render
from django.utils.html import escape
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
import logging
from .models import Room, Member, Route, Score, update_scores
from .serializers import (
    RoomSerializer, MemberSerializer, RouteSerializer,
    RouteCreateSerializer, RouteUpdateSerializer, LeaderboardSerializer, ScoreUpdateSerializer
)
from .permissions import IsAuthenticatedOrReadOnlyForCreate
from .utils import get_log_file_path, get_logs_directory, get_platform_info, is_mobile_device

logger = logging.getLogger(__name__)


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
        
        # 處理 member_completions：FormData 可能將值作為列表傳遞（QueryDict），取第一個元素
        # 如果已經是字典，轉換為 JSON 字符串（因為 serializer 期望字符串）
        data = request.data.copy()
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
        route_id = kwargs.get('pk')
        logger.info(f"[RouteViewSet.update] 開始更新路線 ID: {route_id}")
        
        try:
            route = self.get_object()
            logger.debug(f"[RouteViewSet.update] 獲取路線對象成功: {route.id}, 名稱: {route.name}")
            
            data = request.data.copy()
            logger.debug(f"[RouteViewSet.update] 接收到的數據字段: {list(data.keys())}")
            
            # 清理用戶輸入，防止 XSS
            if 'name' in data:
                original_name = data['name']
                data['name'] = escape(data['name'])
                logger.debug(f"[RouteViewSet.update] 清理路線名稱: '{original_name}' -> '{data['name']}'")
            if 'grade' in data:
                original_grade = data['grade']
                data['grade'] = escape(data['grade'])
                logger.debug(f"[RouteViewSet.update] 清理難度等級: '{original_grade}' -> '{data['grade']}'")
            
            # 處理 member_completions：FormData 可能將值作為列表傳遞（QueryDict），取第一個元素
            # 如果已經是字典，轉換為 JSON 字符串（因為 serializer 期望字符串）
            if 'member_completions' in data:
                member_completions = data['member_completions']
                logger.debug(f"[RouteViewSet.update] member_completions 原始類型: {type(member_completions)}, 值: {member_completions}")
                
                if isinstance(member_completions, list):
                    member_completions = member_completions[0] if len(member_completions) > 0 else '{}'
                    logger.debug(f"[RouteViewSet.update] member_completions 從列表提取: {member_completions}")
                if isinstance(member_completions, dict):
                    import json
                    member_completions = json.dumps(member_completions)
                    logger.debug(f"[RouteViewSet.update] member_completions 從字典轉換為 JSON: {member_completions}")
                if not isinstance(member_completions, str):
                    member_completions = str(member_completions)
                    logger.debug(f"[RouteViewSet.update] member_completions 轉換為字符串: {member_completions}")
                data['member_completions'] = member_completions
            
            # 處理 photo_url：如果存在但為空或無效，移除它（避免 URLField 驗證錯誤）
            # 注意：如果前端沒有發送 photo_url，則不處理（保持現有值）
            if 'photo_url' in data:
                photo_url = data['photo_url']
                logger.debug(f"[RouteViewSet.update] photo_url 原始值類型: {type(photo_url)}, 值: {photo_url}")
                
                # 如果是列表（FormData 可能將值作為列表），取第一個元素
                if isinstance(photo_url, list):
                    photo_url = photo_url[0] if len(photo_url) > 0 else ''
                    logger.debug(f"[RouteViewSet.update] photo_url 從列表提取: {photo_url}")
                
                # 如果是空字符串或無效值，移除該字段（不更新 photo_url）
                if not photo_url or (isinstance(photo_url, str) and photo_url.strip() == ''):
                    logger.warning(f"[RouteViewSet.update] photo_url 為空或無效，移除該字段以避免驗證錯誤")
                    data.pop('photo_url', None)
                # 如果是字符串但不符合基本 URL 格式，也移除
                elif isinstance(photo_url, str):
                    photo_url = photo_url.strip()
                    if not (photo_url.startswith('http://') or photo_url.startswith('https://') or 
                            photo_url.startswith('/') or photo_url.startswith('data:')):
                        logger.warning(f"[RouteViewSet.update] photo_url 不符合 URL 格式: '{photo_url}'，移除該字段")
                        data.pop('photo_url', None)
                    else:
                        logger.debug(f"[RouteViewSet.update] photo_url 驗證通過: {photo_url}")
            
            # 處理照片文件
            if 'photo' in data:
                photo = data['photo']
                if photo:
                    logger.debug(f"[RouteViewSet.update] 收到照片文件: 名稱={getattr(photo, 'name', 'N/A')}, "
                                f"大小={getattr(photo, 'size', 'N/A')}, "
                                f"content_type={getattr(photo, 'content_type', 'N/A')}")
                else:
                    logger.debug(f"[RouteViewSet.update] photo 字段存在但為空")
            
            logger.debug(f"[RouteViewSet.update] 準備傳遞給 serializer 的數據字段: {list(data.keys())}")
            
            serializer = self.get_serializer(route, data=data, partial=True, context={'request': request})
            
            logger.debug(f"[RouteViewSet.update] 開始驗證數據...")
            if not serializer.is_valid():
                logger.error(f"[RouteViewSet.update] 數據驗證失敗！路線 ID: {route_id}")
                logger.error(f"[RouteViewSet.update] 驗證錯誤詳情: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            logger.debug(f"[RouteViewSet.update] 數據驗證通過，開始保存...")
            serializer.save()
            logger.info(f"[RouteViewSet.update] 路線更新成功: {route_id}")
            
            # 重新從數據庫獲取路線，確保包含最新的 scores
            route.refresh_from_db()
            route_serializer = RouteSerializer(route, context={'request': request})
            logger.debug(f"[RouteViewSet.update] 返回更新後的路線數據")
            return Response(route_serializer.data)
            
        except Exception as e:
            import traceback
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            
            logger.exception(f"[RouteViewSet.update] 更新路線時發生未預期的錯誤！路線 ID: {route_id}")
            logger.error(f"[RouteViewSet.update] 錯誤類型: {type(e).__name__}")
            logger.error(f"[RouteViewSet.update] 錯誤信息: {str(e)}")
            logger.error(f"[RouteViewSet.update] 錯誤模塊: {type(e).__module__}")
            logger.error(f"[RouteViewSet.update] 錯誤文件: {exc_traceback.tb_frame.f_code.co_filename if exc_traceback else 'N/A'}")
            logger.error(f"[RouteViewSet.update] 錯誤行號: {exc_traceback.tb_lineno if exc_traceback else 'N/A'}")
            
            # 記錄完整的堆棧跟踪
            full_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
            logger.error(f"[RouteViewSet.update] 完整錯誤堆棧:\n{''.join(full_traceback)}")
            
            # 記錄所有堆棧幀
            if exc_traceback:
                logger.error(f"[RouteViewSet.update] 堆棧幀詳情:")
                frame = exc_traceback
                frame_num = 0
                while frame:
                    logger.error(f"  幀 {frame_num}: {frame.tb_frame.f_code.co_filename}:{frame.tb_lineno} in {frame.tb_frame.f_code.co_name}")
                    # 記錄局部變量（如果可能）
                    try:
                        local_vars = frame.tb_frame.f_locals
                        if 'photo' in local_vars:
                            photo_obj = local_vars['photo']
                            logger.error(f"    局部變量 'photo': 類型={type(photo_obj)}, 名稱={getattr(photo_obj, 'name', 'N/A')}")
                        if 'validated_data' in local_vars:
                            logger.error(f"    局部變量 'validated_data': 鍵={list(local_vars['validated_data'].keys())}")
                    except:
                        pass
                    frame = frame.tb_next
                    frame_num += 1
                    if frame_num > 50:  # 限制最多50個幀
                        logger.error(f"  ... (還有更多幀)")
                        break
            
            # 檢查是否為 pickle 錯誤
            if 'pickle' in str(e).lower() or 'BufferedRandom' in str(e) or 'BufferedReader' in str(e):
                logger.critical(f"[RouteViewSet.update] ⚠️ 檢測到 PICKLE 錯誤！")
                logger.critical(f"[RouteViewSet.update] 這通常發生在嘗試序列化 BufferedRandom 或 BufferedReader 對象時")
                logger.critical(f"[RouteViewSet.update] 請檢查文件對象是否在保存前被正確轉換為 InMemoryUploadedFile")
            
            return Response(
                {'detail': f'更新路線時發生錯誤: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """刪除路線"""
        route = self.get_object()
        room_id = route.room.id
        
        # 刪除路線（會級聯刪除相關的 Score 記錄）
        route.delete()
        
        # 觸發計分更新
        update_scores(room_id)
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], url_path='log-info')
    def log_info(self, request):
        """
        獲取日誌文件信息（用於移動設備調試）
        返回日誌文件位置和平台信息
        """
        try:
            log_file_path = get_log_file_path()
            logs_dir = get_logs_directory()
            
            # 檢查日誌文件是否存在
            from pathlib import Path
            log_file = Path(log_file_path)
            file_exists = log_file.exists()
            file_size = log_file.stat().st_size if file_exists else 0
            
            # 獲取平台信息
            platform_info = get_platform_info()
            
            return Response({
                'log_file_path': log_file_path,
                'logs_directory': str(logs_dir),
                'file_exists': file_exists,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2) if file_size > 0 else 0,
                'is_mobile': is_mobile_device(),
                'platform_info': platform_info,
                'message': '日誌文件已配置。在移動設備上，日誌文件會自動保存到應用數據目錄。'
            })
        except Exception as e:
            logger.exception(f"[RouteViewSet.log_info] 獲取日誌信息時發生錯誤")
            return Response({
                'error': str(e),
                'message': '無法獲取日誌文件信息'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        try:
            member = self.get_object()
        except Exception as e:
            # 如果成員不存在，返回 404
            return Response(
                {'detail': '找不到指定的成員', 'error': str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        
        room_id = member.room.id
        
        try:
            # 刪除成員（會級聯刪除相關的 Score 記錄）
            member.delete()
            
            # 觸發計分更新（會自動更新standard_line_score）
            update_scores(room_id)
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            # 刪除失敗，返回錯誤信息
            return Response(
                {'detail': '刪除成員時發生錯誤', 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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

