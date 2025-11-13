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
from .serializers import convert_file_to_uploaded_file

logger = logging.getLogger(__name__)

# PDF 导出相关导入
try:
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as PDFImage, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab 未安装，PDF 导出功能将不可用。请运行: pip install reportlab")


def get_dynamic_permissions(viewset_instance):
    """
    動態獲取權限類，支持 @override_settings
    用於 ViewSet 的 get_permissions() 方法
    """
    import sys
    is_test = 'test' in sys.argv or 'pytest' in sys.modules or 'unittest' in sys.modules
    
    # 動態讀取設置，支持 @override_settings
    from django.conf import settings as django_settings
    rest_framework_config = getattr(django_settings, 'REST_FRAMEWORK', {})
    default_perms = rest_framework_config.get('DEFAULT_PERMISSION_CLASSES', [])
    
    if is_test:
        viewset_name = viewset_instance.__class__.__name__
        print(f"\n[DEBUG] {viewset_name}.get_permissions:")
        print(f"  DEFAULT_PERMISSION_CLASSES = {default_perms}")
    
    # 如果設置了權限類，使用設置的權限類
    if default_perms:
        from django.utils.module_loading import import_string
        permission_classes = []
        for perm_class in default_perms:
            if isinstance(perm_class, str):
                permission_classes.append(import_string(perm_class))
            else:
                permission_classes.append(perm_class)
        
        if is_test:
            print(f"  Using permission classes = {[p.__name__ for p in permission_classes]}")
        
        # 創建權限實例
        return [perm() for perm in permission_classes]
    
    # 如果沒有設置，使用父類的默認行為
    permissions_list = super(viewset_instance.__class__, viewset_instance).get_permissions()
    if is_test:
        print(f"  Using default permission classes = {[type(p).__name__ for p in permissions_list]}")
    return permissions_list


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    # 使用 settings.py 中的默認權限設置（開發環境為 AllowAny）
    
    def get_permissions(self):
        """獲取權限類（動態讀取設置，支持 @override_settings）"""
        return get_dynamic_permissions(self)
    
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

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """導出排行榜PDF，包含照片和測項"""
        if not REPORTLAB_AVAILABLE:
            return Response(
                {'detail': 'PDF 导出功能不可用，请安装 reportlab: pip install reportlab'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        from django.http import HttpResponse
        from io import BytesIO
        import os
        from PIL import Image as PILImage
        
        try:
            room = self.get_object()
        except Exception as e:
            logger.error(f"獲取房間對象時發生錯誤: {e}")
            return Response(
                {'detail': '找不到指定的房間'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 創建PDF緩衝區
        buffer = BytesIO()
        # 設置PDF標題（用於PDF查看器的標題欄顯示）
        pdf_title = f"{room.name} - 總表"
        
        # 創建自定義文檔模板，設置標題和作者
        # 將 pdf_title 作為類變量傳遞，確保 Python 3.8 兼容性
        class CustomDocTemplate(SimpleDocTemplate):
            def __init__(self, *args, **kwargs):
                # 從 kwargs 中提取 pdf_title，如果存在則存儲為實例變量
                self.pdf_title_value = kwargs.pop('pdf_title_value', None)
                super(CustomDocTemplate, self).__init__(*args, **kwargs)
            
            def build(self, flowables, onFirstPage=None, onLaterPages=None, canvasmaker=None):
                # 使用實例變量而不是閉包變量，確保 Python 3.8 兼容性
                pdf_title_for_metadata = self.pdf_title_value
                
                # 設置PDF元數據
                def set_metadata(canvas, doc):
                    canvas.setTitle(pdf_title_for_metadata)
                    canvas.setAuthor("攀岩計分系統")
                    canvas.setSubject("排行榜導出")
                
                # 如果沒有提供 onFirstPage，使用默認的元數據設置
                if onFirstPage is None:
                    onFirstPage = set_metadata
                else:
                    # 如果提供了 onFirstPage，組合兩個函數
                    original_onFirstPage = onFirstPage
                    def combined_onFirstPage(canvas, doc):
                        set_metadata(canvas, doc)
                        if original_onFirstPage:
                            original_onFirstPage(canvas, doc)
                    onFirstPage = combined_onFirstPage
                
                # 構建參數字典，只包含非 None 的參數
                build_kwargs = {
                    'onFirstPage': onFirstPage,
                }
                if onLaterPages is not None:
                    build_kwargs['onLaterPages'] = onLaterPages
                if canvasmaker is not None:
                    build_kwargs['canvasmaker'] = canvasmaker
                
                # 使用顯式的 super() 調用以確保 Python 3.8 兼容性
                super(CustomDocTemplate, self).build(flowables, **build_kwargs)
        
        doc = CustomDocTemplate(buffer, pagesize=A4, 
                                rightMargin=0.5*inch, leftMargin=0.5*inch,
                                topMargin=0.5*inch, bottomMargin=0.5*inch,
                                title=pdf_title, pdf_title_value=pdf_title)
        
        # 註冊中文字體（嘗試使用系統字體）
        # 如果系統沒有中文字體，可以使用 reportlab 的 CJK 支持或下載字體文件
        try:
            # 嘗試註冊常見的中文字體
            font_paths = [
                'C:/Windows/Fonts/msjh.ttc',  # 微軟正黑體 (Windows)
                'C:/Windows/Fonts/simsun.ttc',  # 宋體 (Windows)
                '/System/Library/Fonts/PingFang.ttc',  # 蘋方 (macOS)
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',  # 文泉驛微米黑 (Linux)
            ]
            
            chinese_font_registered = False
            chinese_font_name = 'ChineseFont'
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(chinese_font_name, font_path))
                        chinese_font_registered = True
                        logger.info(f"成功註冊中文字體: {font_path}")
                        break
                    except Exception as e:
                        logger.warning(f"註冊字體失敗 {font_path}: {e}")
                        continue
            
            # 如果沒有找到系統字體，使用 reportlab 的內置支持（需要安裝 reportlab-cjk）
            if not chinese_font_registered:
                try:
                    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
                    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))  # 宋體
                    chinese_font_name = 'STSong-Light'
                    chinese_font_registered = True
                    logger.info("使用 reportlab CJK 字體支持")
                except ImportError:
                    logger.warning("未找到中文字體，中文可能無法正確顯示。建議安裝 reportlab-cjk 或配置系統字體")
                    chinese_font_name = 'Helvetica'  # 回退到默認字體
        except Exception as e:
            logger.error(f"字體註冊錯誤: {e}")
            chinese_font_name = 'Helvetica'
        
        # 獲取樣式
        styles = getSampleStyleSheet()
        
        # 創建自定義樣式（使用中文字體）
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=chinese_font_name,
            fontSize=18,
            textColor=colors.HexColor('#2C3E50'),
            spaceAfter=12,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontName=chinese_font_name,
            fontSize=14,
            textColor=colors.HexColor('#34495E'),
            spaceAfter=10,
            alignment=TA_LEFT
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName=chinese_font_name,
            fontSize=10
        )
        
        # 構建PDF內容
        story = []
        
        # 標題
        title = Paragraph(f"{room.name} - 排行榜", title_style)
        story.append(title)
        story.append(Spacer(1, 0.2*inch))
        
        # 房間信息
        info_text = f"房間 ID: {room.id} | 每一條線總分 (L): {room.standard_line_score}"
        story.append(Paragraph(info_text, normal_style))
        story.append(Spacer(1, 0.3*inch))
        
        # 獲取成員數據（按總分降序）
        members = room.members.all().order_by('-total_score', 'name')
        
        # 先收集所有成員完成的所有路線的等級（用於確定需要哪些等級欄位）
        all_completed_grades = set()
        for member in members:
            completed_scores = member.scores.filter(is_completed=True).select_related('route')
            for score in completed_scores:
                grade = score.route.grade
                if grade:  # 只收集有等級的路線
                    all_completed_grades.add(grade)
        
        # 等級排序函數：將等級轉換為可排序的數值
        def sort_grade(grade):
            """排序函數：將等級轉換為可排序的數值"""
            if not grade or grade == '未知':
                return (0, 0)  # 未知等級排最後
            grade = grade.strip().upper()
            # 處理 V8+ 這種格式
            if grade.endswith('+'):
                base_grade = grade[:-1]
                try:
                    num = int(base_grade.replace('V', ''))
                    return (num, 1)  # + 表示 0.5
                except:
                    return (0, 0)
            # 處理普通 V5 格式
            try:
                num = int(grade.replace('V', ''))
                return (num, 0)
            except:
                return (0, 0)
        
        # 按等級從高到低排序
        sorted_all_grades = sorted(all_completed_grades, key=sort_grade, reverse=True)
        
        # 構建表頭：排名、成員、總分、完成總條數、各等級欄位、是否客製化組
        table_headers = ['排名', '成員', '總分', '完成總條數'] + sorted_all_grades + ['是否客製化組']
        leaderboard_data = [table_headers]
        
        current_rank = 1
        previous_score = None
        
        for index, member in enumerate(members, start=1):
            current_score = float(member.total_score)
            
            # 第一個成員始終是第1名
            if index == 1:
                current_rank = 1
            else:
                # 如果分數與前一個不同，更新排名為當前索引
                if previous_score is not None and current_score != previous_score:
                    current_rank = index
                # 如果分數相同，保持當前排名（不更新 current_rank）
            
            previous_score = current_score
            
            custom_text = '是' if member.is_custom_calc else '否'
            completed_count = member.completed_routes_count
            
            # 計算成員通過的路線等級統計
            completed_scores = member.scores.filter(is_completed=True).select_related('route')
            grade_count = {}
            for score in completed_scores:
                grade = score.route.grade
                if grade:  # 只統計有等級的路線
                    grade_count[grade] = grade_count.get(grade, 0) + 1
            
            # 構建行數據：排名、成員、總分、完成總條數、各等級數量、是否客製化組
            row_data = [
                str(current_rank),
                member.name,
                f"{current_score:.2f}",
                str(completed_count)
            ]
            
            # 為每個等級欄位添加該成員完成該等級的數量
            for grade in sorted_all_grades:
                count = grade_count.get(grade, 0)
                row_data.append(str(count) if count > 0 else '-')
            
            row_data.append(custom_text)
            leaderboard_data.append(row_data)
        
        # 計算列寬：基本列 + 每個等級列 + 最後一列
        base_col_widths = [0.8*inch, 2*inch, 1*inch, 1*inch]  # 排名、成員、總分、完成總條數
        grade_col_width = 0.7*inch  # 每個等級欄位寬度
        grade_col_widths = [grade_col_width] * len(sorted_all_grades)
        last_col_width = 1.2*inch  # 是否客製化組
        col_widths = base_col_widths + grade_col_widths + [last_col_width]
        
        # 創建排行榜表格
        leaderboard_table = Table(leaderboard_data, colWidths=col_widths)
        
        # 計算等級欄位的列索引範圍
        # 表頭結構：排名(0) | 成員(1) | 總分(2) | 完成總條數(3) | 等級欄位(4~3+len) | 是否客製化組(最後)
        grade_col_start = 4  # 等級欄位開始的列索引
        grade_col_end = 3 + len(sorted_all_grades)  # 等級欄位結束的列索引
        
        leaderboard_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 默認居中
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # 成員名稱左對齊
            # 等級欄位居中对齐
            ('ALIGN', (grade_col_start, 0), (grade_col_end, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), chinese_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), chinese_font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(Paragraph("排行榜", heading_style))
        story.append(leaderboard_table)
        story.append(Spacer(1, 0.5*inch))
        story.append(PageBreak())
        
        # 路線列表（測項）- 總表格式
        story.append(Paragraph("路線列表", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # 獲取所有成員（按名稱排序，保持一致性）
        all_members = room.members.all().order_by('name')
        member_names = [member.name for member in all_members]
        
        # 獲取路線數據，按難度遞減排序
        # 使用與排行榜相同的等級排序函數
        def sort_grade_for_route(route):
            """排序函數：將路線等級轉換為可排序的數值"""
            grade = route.grade
            if not grade or grade == '未知':
                return (0, 0)  # 未知等級排最後
            grade = grade.strip().upper()
            # 處理 V8+ 這種格式
            if grade.endswith('+'):
                base_grade = grade[:-1]
                try:
                    num = int(base_grade.replace('V', ''))
                    return (num, 1)  # + 表示 0.5
                except:
                    return (0, 0)
            # 處理普通 V5 格式
            try:
                num = int(grade.replace('V', ''))
                return (num, 0)
            except:
                return (0, 0)
        
        # 獲取所有路線並按難度排序（從高到低）
        all_routes = list(room.routes.all())
        routes = sorted(all_routes, key=sort_grade_for_route, reverse=True)
        
        # 用於保存所有臨時文件路徑，以便最後清理
        temp_files = []
        
        # 構建總表：路線名稱、難度等級、完成人數、照片、每個成員的完成狀態（1/0）
        # 表頭
        route_table_headers = ['路線名稱', '難度等級', '完成人數', '照片'] + member_names
        
        # 計算列寬（根據內容動態調整）
        # 基本列寬
        photo_col_width = 1.8*inch  # 照片列寬度（增大）
        col_widths = [2*inch, 1*inch, 1*inch, photo_col_width]  # 路線名稱、難度、完成人數、照片
        # 每個成員列寬度
        member_col_width = 0.6*inch
        col_widths.extend([member_col_width] * len(member_names))
        
        # 構建表格數據
        route_table_data = [route_table_headers]
        
        # 處理每個路線（先處理照片，準備嵌入表格）
        route_photos = {}  # 存儲路線照片對象
        photo_height = 1.0*inch  # 照片在表格中的高度（增大）
        
        # 如果沒有路線，添加提示行
        if len(routes) == 0:
            route_table_data.append([
                '暫無路線',
                '-',
                '-',
                Paragraph('無', normal_style)
            ] + ['-' for _ in member_names])
        else:
            for route in routes:
                # 處理照片
                if route.photo:
                    try:
                        photo_path = route.photo.path
                        if os.path.exists(photo_path):
                            # 調整照片大小以適應表格單元格
                            img = PILImage.open(photo_path)
                            # 計算適合表格單元格的尺寸
                            max_width_px = int(photo_col_width * 72)  # 轉換為點（points）
                            max_height_px = int(photo_height * 72)
                            
                            # 按比例縮放
                            width_ratio = max_width_px / img.width if img.width > 0 else 1
                            height_ratio = max_height_px / img.height if img.height > 0 else 1
                            scale_ratio = min(width_ratio, height_ratio, 1.0)  # 不放大，只縮小
                            
                            new_width = int(img.width * scale_ratio)
                            new_height = int(img.height * scale_ratio)
                            
                            if scale_ratio < 1.0:
                                # 兼容旧版本 Pillow：PILImage.Resampling 在 Pillow 10.0.0+ 才可用
                                try:
                                    resample = PILImage.Resampling.LANCZOS
                                except AttributeError:
                                    resample = PILImage.LANCZOS
                                img = img.resize((new_width, new_height), resample)
                            
                            # 保存臨時圖片
                            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_export')
                            os.makedirs(temp_dir, exist_ok=True)
                            temp_path = os.path.join(temp_dir, f'route_{route.id}.jpg')
                            img.save(temp_path, 'JPEG', quality=85)
                            temp_files.append(temp_path)
                            
                            # 創建 PDF Image 對象（使用英寸單位）
                            # 確保尺寸不為0，並且限制最大高度
                            if new_width > 0 and new_height > 0:
                                # 限制照片最大高度為 1.0 英寸（72 點），寬度為 1.8 英寸（129.6 點）
                                max_img_height_points = 72  # 1.0 inch = 72 points
                                max_img_width_points = 129.6  # 1.8 inch = 129.6 points
                                
                                # 如果高度或寬度超過限制，按比例縮小
                                if new_height > max_img_height_points:
                                    height_scale = max_img_height_points / new_height
                                    new_width = int(new_width * height_scale)
                                    new_height = max_img_height_points
                                
                                if new_width > max_img_width_points:
                                    width_scale = max_img_width_points / new_width
                                    new_height = int(new_height * width_scale)
                                    new_width = max_img_width_points
                                
                                img_width_inch = new_width / 72.0  # 點轉換為英寸
                                img_height_inch = new_height / 72.0
                                pdf_img = PDFImage(temp_path, width=img_width_inch*inch, height=img_height_inch*inch)
                                route_photos[route.id] = pdf_img
                            else:
                                route_photos[route.id] = Paragraph('照片尺寸錯誤', normal_style)
                        else:
                            route_photos[route.id] = Paragraph('照片不存在', normal_style)
                    except Exception as e:
                        logger.error(f"處理路線照片時發生錯誤: {e}")
                        route_photos[route.id] = Paragraph('照片載入失敗', normal_style)
                else:
                    route_photos[route.id] = Paragraph('無照片', normal_style)
            
            # 構建表格數據行
            for route in routes:
                # 計算完成人數
                completed_count = route.scores.filter(is_completed=True).count()
                total_count = route.scores.count()
                completion_text = f"{completed_count}/{total_count}"
                
                # 獲取該路線的所有成績記錄
                route_scores = {score.member_id: score.is_completed for score in route.scores.all()}
                
                # 構建行數據（照片列使用 Image 對象或 Paragraph）
                row_data = [
                    route.name,
                    route.grade or '-',
                    completion_text,
                    route_photos.get(route.id, Paragraph('無照片', normal_style))  # 嵌入照片或文字
                ]
                
                # 添加每個成員的完成狀態（1=完成，0=未完成）
                for member in all_members:
                    is_completed = route_scores.get(member.id, False)
                    row_data.append('1' if is_completed else '0')
                
                route_table_data.append(row_data)
        
        # 創建路線總表（只有在有數據時才設置 repeatRows）
        # 使用 splitByRow 允許表格跨頁，並設置最大行高
        if len(route_table_data) > 1:  # 有數據行
            route_table = Table(route_table_data, colWidths=col_widths, repeatRows=1, splitByRow=1)
        else:
            route_table = Table(route_table_data, colWidths=col_widths, splitByRow=1)
        route_table.setStyle(TableStyle([
            # 表頭樣式
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),  # 路線名稱左對齊
            ('FONTNAME', (0, 0), (-1, 0), chinese_font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            # 數據行樣式
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), chinese_font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # 照片列特殊處理：垂直和水平居中
            ('VALIGN', (3, 1), (3, -1), 'MIDDLE'),  # 照片列垂直居中
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),   # 照片列水平居中
            # 交替行背景色（可選）
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            # 設置行高和內邊距（適應較大的照片）
            ('LEFTPADDING', (3, 1), (3, -1), 4),    # 照片列左右內邊距
            ('RIGHTPADDING', (3, 1), (3, -1), 4),
            ('TOPPADDING', (3, 1), (3, -1), 4),     # 照片列上下內邊距
            ('BOTTOMPADDING', (3, 1), (3, -1), 4),
            # 數據行內邊距
            ('TOPPADDING', (0, 1), (-1, -1), 4),    # 所有數據行上下內邊距
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))
        
        story.append(route_table)
        story.append(Spacer(1, 0.3*inch))
        
        # 構建PDF（添加錯誤處理）
        try:
            doc.build(story)
        except Exception as build_error:
            logger.error(f"構建PDF時發生錯誤: {build_error}")
            import traceback
            logger.error(f"錯誤堆棧: {traceback.format_exc()}")
            # 清理臨時文件
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
            try:
                buffer.close()
            except Exception:
                pass
            # 返回錯誤響應
            return Response(
                {'detail': f'PDF 生成失敗: {str(build_error)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 保存完成後，清理所有臨時文件
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception as cleanup_error:
                logger.warning(f"清理臨時文件失敗 {temp_file}: {cleanup_error}")
        
        # 獲取PDF內容
        try:
            pdf_content = buffer.getvalue()
        except Exception as e:
            logger.error(f"獲取PDF內容時發生錯誤: {e}")
            buffer.close()
            return Response(
                {'detail': 'PDF 內容獲取失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            try:
                buffer.close()
            except Exception:
                pass
        
        # 創建HTTP響應
        try:
            response = HttpResponse(pdf_content, content_type='application/pdf')
            filename = f"{room.name}_排行榜_{room.id}.pdf"
            # 處理中文文件名
            from urllib.parse import quote
            response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"; filename*=UTF-8\'\'{quote(filename)}'
            return response
        except Exception as e:
            logger.error(f"創建HTTP響應時發生錯誤: {e}")
            return Response(
                {'detail': 'PDF 響應創建失敗'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
    
    def get_permissions(self):
        """獲取權限類（動態讀取設置，支持 @override_settings）"""
        return get_dynamic_permissions(self)

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
    
    def get_permissions(self):
        """獲取權限類（動態讀取設置，支持 @override_settings）"""
        return get_dynamic_permissions(self)
    
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
            
            # 在複製 request.data 之前，先處理文件對象（避免 pickle 錯誤）
            # 如果直接使用 request.data.copy()，Django 會嘗試深拷貝，導致 BufferedRandom 無法序列化
            # 需要同時支持 JSON 格式（普通字典）和 FormData 格式（QueryDict）
            from django.http import QueryDict
            
            data = {}
            # 檢查 request.data 是 QueryDict（FormData）還是普通字典（JSON）
            is_querydict = isinstance(request.data, QueryDict)
            
            for key in request.data.keys():
                # QueryDict 的 getlist 方法可以獲取所有值（包括列表）
                # 如果是普通字典，直接獲取值
                if is_querydict:
                    values = request.data.getlist(key)
                else:
                    # JSON 格式：直接獲取值，如果是列表則保持列表，否則包裝成列表以便統一處理
                    value = request.data.get(key)
                    values = [value] if value is not None else []
                
                # 如果是文件對象（photo 字段），只取第一個值並轉換
                if key == 'photo' and values:
                    photo_value = values[0] if values else None
                    if photo_value:
                        logger.debug(f"[RouteViewSet.update] 檢測到照片文件，原始類型: {type(photo_value)}")
                        try:
                            # 轉換文件對象為 InMemoryUploadedFile
                            converted_photo = convert_file_to_uploaded_file(photo_value)
                            logger.debug(f"[RouteViewSet.update] 照片文件已轉換，新類型: {type(converted_photo)}")
                            data[key] = converted_photo
                        except Exception as e:
                            logger.error(f"[RouteViewSet.update] 轉換照片文件時發生錯誤: {e}")
                            # 如果轉換失敗，仍然嘗試使用原文件（可能會導致錯誤，但至少記錄了錯誤）
                            data[key] = photo_value
                    else:
                        data[key] = None
                else:
                    # 非文件字段，處理列表值（QueryDict 可能返回列表）
                    if len(values) == 1:
                        data[key] = values[0]
                    else:
                        data[key] = values
            
            logger.debug(f"[RouteViewSet.update] 接收到的數據字段: {list(data.keys())}")
            
            # 清理用戶輸入，防止 XSS
            if 'name' in data:
                original_name = data['name']
                # 確保 name 是字符串（如果是列表，取第一個元素）
                if isinstance(original_name, list):
                    original_name = original_name[0] if len(original_name) > 0 else ''
                if isinstance(original_name, str):
                    data['name'] = escape(original_name)
                else:
                    data['name'] = str(original_name)
                logger.debug(f"[RouteViewSet.update] 清理路線名稱: '{original_name}' -> '{data['name']}'")
            if 'grade' in data:
                original_grade = data['grade']
                # 確保 grade 是字符串（如果是列表，取第一個元素）
                if isinstance(original_grade, list):
                    original_grade = original_grade[0] if len(original_grade) > 0 else ''
                if isinstance(original_grade, str):
                    data['grade'] = escape(original_grade)
                else:
                    data['grade'] = str(original_grade)
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
    
    def get_permissions(self):
        """獲取權限類（動態讀取設置，支持 @override_settings）"""
        return get_dynamic_permissions(self)

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

