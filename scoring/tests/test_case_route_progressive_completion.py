from django.test import TestCase
from scoring.models import Room, Member, Route, Score, update_scores
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data


class TestCaseRouteProgressiveCompletion(TestCase):
    """測試案例：路線逐步完成場景（非客製化成員）"""

    def setUp(self):
        """設置測試數據"""
        self.room = TestDataFactory.create_room(name="測試房間")
        # 創建兩個非客製化成員（一般組）
        self.m1, self.m2 = TestDataFactory.create_normal_members(
            self.room,
            count=2,
            names=["王小明", "李大華"]
        )
        # 2個一般組成員，L = LCM(1,2) = 2

    def update_scores(self):
        """更新分數"""
        update_scores(self.room.id)

    def test_route_progressive_completion(self):
        """測試路線逐步完成場景"""
        # 刷新房間以獲取最新的 standard_line_score
        self.room.refresh_from_db()
        L = self.room.standard_line_score  # 應該是 2（LCM(1,2) = 2）

        # 步驟 1: 建立新路線，建立時無人完成
        r1 = Route.objects.create(room=self.room, name="路線1", grade="V3")
        Score.objects.create(member=self.m1, route=r1, is_completed=False)
        Score.objects.create(member=self.m2, route=r1, is_completed=False)
        self.update_scores()
        
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 驗證：無人完成，所有人分數應該為 0
        self.assertEqual(float(self.m1.total_score), 0.00)
        self.assertEqual(float(self.m2.total_score), 0.00)
        # 驗證：路線完成人數 = 0
        normal_completers = Score.objects.filter(
            route=r1,
            is_completed=True,
            member__is_custom_calc=False
        ).count()
        self.assertEqual(normal_completers, 0)

        # 步驟 2: M1 完成路線
        score_m1 = Score.objects.get(member=self.m1, route=r1)
        score_m1.is_completed = True
        score_m1.save()
        self.update_scores()
        
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 驗證：1人完成，完成者獲得全部分數 L
        # L = 2，完成人數 = 1，每人得 2/1 = 2分
        self.assertEqual(float(self.m1.total_score), 2.00)
        self.assertEqual(float(self.m2.total_score), 0.00)
        # 驗證：路線完成人數 = 1
        normal_completers = Score.objects.filter(
            route=r1,
            is_completed=True,
            member__is_custom_calc=False
        ).count()
        self.assertEqual(normal_completers, 1)

        # 步驟 3: M2 也完成路線
        score_m2 = Score.objects.get(member=self.m2, route=r1)
        score_m2.is_completed = True
        score_m2.save()
        self.update_scores()
        
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 驗證：2人完成，每人獲得 L/2 分
        # L = 2，完成人數 = 2，每人得 2/2 = 1分
        # 注意：M1 之前的分數會被重新計算
        self.assertEqual(float(self.m1.total_score), 1.00)
        self.assertEqual(float(self.m2.total_score), 1.00)
        # 驗證：路線完成人數 = 2
        normal_completers = Score.objects.filter(
            route=r1,
            is_completed=True,
            member__is_custom_calc=False
        ).count()
        self.assertEqual(normal_completers, 2)
    
    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

