from django.db import models
from django.db.models import Count, Q, Sum
from decimal import Decimal
import math


def lcm(a, b):
    """計算兩個數的最小公倍數"""
    return abs(a * b) // math.gcd(a, b) if a and b else 0


def lcm_of_list(numbers):
    """計算列表中所有數的最小公倍數"""
    if not numbers:
        return 1
    if len(numbers) == 1:
        return numbers[0]
    result = numbers[0]
    for i in range(1, len(numbers)):
        result = lcm(result, numbers[i])
    return result


class Room(models.Model):
    """房間/比賽資訊"""
    name = models.CharField(max_length=200, verbose_name='房間名稱')
    standard_line_score = models.IntegerField(default=1, verbose_name='每一條路線總分 (L)')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '房間'
        verbose_name_plural = '房間'

    def __str__(self):
        return self.name

    def calculate_standard_line_score(self):
        """
        計算每一條線總分
        - 如果一般組成員數低於8人：使用1到成員數的最小公倍數
        - 如果一般組成員數高於或等於8人：固定為1000分
        如果沒有一般組成員，返回預設值1
        """
        normal_members = self.members.filter(is_custom_calc=False)
        if not normal_members.exists():
            return 1
        
        # 獲取所有一般組成員的數量
        member_count = normal_members.count()
        if member_count == 0:
            return 1
        
        # 如果成員數高於或等於8人，固定為1000分
        if member_count >= 8:
            return 1000
        
        # 如果成員數低於8人，計算1到member_count的最小公倍數
        # 這是因為每條路線完成的人數可能是1到N（N為一般組成員數）
        numbers = list(range(1, member_count + 1))
        return lcm_of_list(numbers)

    def update_standard_line_score(self):
        """更新standard_line_score為計算出的值"""
        calculated_score = self.calculate_standard_line_score()
        if self.standard_line_score != calculated_score:
            self.standard_line_score = calculated_score
            self.save(update_fields=['standard_line_score'])


class Member(models.Model):
    """成員列表"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='members', verbose_name='房間')
    name = models.CharField(max_length=100, verbose_name='成員名稱')
    is_custom_calc = models.BooleanField(default=False, verbose_name='是否為客製化組')
    total_score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='總分')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '成員'
        verbose_name_plural = '成員'
        ordering = ['-total_score', 'name']

    def __str__(self):
        return f"{self.name} ({self.room.name})"

    @property
    def completed_routes_count(self):
        """完成的路線數量"""
        return self.scores.filter(is_completed=True).count()


class Route(models.Model):
    """攀岩路線資訊"""
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='routes', verbose_name='房間')
    name = models.CharField(max_length=200, verbose_name='路線名稱')
    grade = models.CharField(max_length=50, blank=True, verbose_name='難度等級')
    photo = models.ImageField(upload_to='route_photos/', blank=True, null=True, verbose_name='照片')
    photo_url = models.URLField(blank=True, verbose_name='照片網址（舊版，已棄用）')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '路線'
        verbose_name_plural = '路線'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} ({self.room.name})"


class Score(models.Model):
    """成績記錄 (核心)"""
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='scores', verbose_name='成員')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='scores', verbose_name='路線')
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    score_attained = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='獲得的分數')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '成績'
        verbose_name_plural = '成績'
        unique_together = ['member', 'route']
        ordering = ['-created_at']

    def __str__(self):
        status = '完成' if self.is_completed else '未完成'
        return f"{self.member.name} - {self.route.name} ({status})"


def update_scores(room_id):
    """
    核心計分邏輯函數
    當 Score 或 Member 狀態變動時觸發
    """
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return

    # 自動更新standard_line_score為一般組成員數的最小公倍數
    room.update_standard_line_score()
    L = room.standard_line_score

    # 獲取所有常態組成員和客製化組成員
    normal_members = room.members.filter(is_custom_calc=False)
    custom_members = room.members.filter(is_custom_calc=True)

    # 1. 常態組計算
    # 獲取所有路線及其完成狀態
    routes = room.routes.all()

    for route in routes:
        # 計算完成該路線的常態組人數 P_r
        normal_completers = Score.objects.filter(
            route=route,
            is_completed=True,
            member__is_custom_calc=False
        ).count()

        # 計算路線分數 S_r = L / P_r (如果 P_r > 0)
        if normal_completers > 0:
            route_score = Decimal(str(L)) / Decimal(str(normal_completers))
        else:
            route_score = Decimal('0.00')

        # 更新所有完成該路線的常態組成員的分數
        normal_scores = Score.objects.filter(
            route=route,
            is_completed=True,
            member__is_custom_calc=False
        )
        for score in normal_scores:
            score.score_attained = route_score
            score.save()

        # 將未完成的常態組成員的分數設為 0
        normal_scores_incomplete = Score.objects.filter(
            route=route,
            is_completed=False,
            member__is_custom_calc=False
        )
        for score in normal_scores_incomplete:
            score.score_attained = Decimal('0.00')
            score.save()

    # 計算每個常態組成員的總分
    for member in normal_members:
        total = Score.objects.filter(
            member=member,
            is_completed=True
        ).aggregate(
            total=Sum('score_attained')
        )['total'] or Decimal('0.00')
        member.total_score = total
        member.save()

    # 2. 客製化組計算
    # 統計客製化成員完成的路線數 N_custom，總分 S_total = N_custom × L
    for member in custom_members:
        completed_count = Score.objects.filter(
            member=member,
            is_completed=True
        ).count()
        member.total_score = Decimal(str(completed_count)) * Decimal(str(L))
        member.save()

        # 同時更新客製化組成員的單線分數記錄
        for score in member.scores.all():
            if score.is_completed:
                score.score_attained = Decimal(str(L))
            else:
                score.score_attained = Decimal('0.00')
            score.save()

