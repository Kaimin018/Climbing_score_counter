"""
測項2：成員和路線操作測試

測試場景：
1. 5個成員（3個一般組，2個客製化組）
2. 新增10條線，計算分數
3. 刪除部分成員，計算分數
4. 刪除部分路線，計算分數
5. 新增部分成員到8人，計算分數
6. 新增路線，計算分數
"""
from django.test import TestCase
from scoring.models import Room, Member, Route, Score, update_scores
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data


class TestCaseMemberRouteOperations(TestCase):
    """測項2：成員和路線操作測試"""

    def setUp(self):
        """設置測試數據"""
        self.room = TestDataFactory.create_room(name="測試房間")
        # 創建3個一般組成員和2個客製化組成員
        self.m1, self.m2, self.m3 = TestDataFactory.create_normal_members(
            self.room,
            count=3,
            names=["一般組1", "一般組2", "一般組3"]
        )
        self.m4, self.m5 = TestDataFactory.create_custom_members(
            self.room,
            count=2,
            names=["客製化1", "客製化2"]
        )
        # 創建成員後需要更新分數以計算L值
        self.update_scores()

    def update_scores(self):
        """更新分數"""
        update_scores(self.room.id)

    def test_member_route_operations(self):
        """測項2：成員和路線操作完整測試"""
        # 步驟1: 5個成員（3個一般組，2個客製化組）
        # 已在setUp中完成
        self.assertEqual(Member.objects.filter(room=self.room, is_custom_calc=False).count(), 3)
        self.assertEqual(Member.objects.filter(room=self.room, is_custom_calc=True).count(), 2)
        
        # 3個一般組成員，L = LCM(1,2,3) = 6
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 6)  # LCM(1,2,3) = 6
        
        # 步驟2: 新增10條線，計算分數
        routes = []
        # 路線1: M1, M2完成（一般組2人完成）
        r1 = TestDataFactory.create_route(
            self.room, name="路線1", grade="V1",
            member_completions={self.m1.id: True, self.m2.id: True}
        )
        routes.append(r1)
        self.update_scores()
        
        # 路線2: M1, M3完成（一般組2人完成）
        r2 = TestDataFactory.create_route(
            self.room, name="路線2", grade="V2",
            member_completions={self.m1.id: True, self.m3.id: True}
        )
        routes.append(r2)
        self.update_scores()
        
        # 路線3: M2, M3完成（一般組2人完成）
        r3 = TestDataFactory.create_route(
            self.room, name="路線3", grade="V3",
            member_completions={self.m2.id: True, self.m3.id: True}
        )
        routes.append(r3)
        self.update_scores()
        
        # 路線4: M1完成（一般組1人完成）
        r4 = TestDataFactory.create_route(
            self.room, name="路線4", grade="V4",
            member_completions={self.m1.id: True}
        )
        routes.append(r4)
        self.update_scores()
        
        # 路線5: M4, M5完成（客製化組2人完成）
        r5 = TestDataFactory.create_route(
            self.room, name="路線5", grade="V5",
            member_completions={self.m4.id: True, self.m5.id: True}
        )
        routes.append(r5)
        self.update_scores()
        
        # 路線6: M1, M4完成（一般組1人，客製化組1人）
        r6 = TestDataFactory.create_route(
            self.room, name="路線6", grade="V6",
            member_completions={self.m1.id: True, self.m4.id: True}
        )
        routes.append(r6)
        self.update_scores()
        
        # 路線7: M2, M4, M5完成（一般組1人，客製化組2人）
        r7 = TestDataFactory.create_route(
            self.room, name="路線7", grade="V7",
            member_completions={self.m2.id: True, self.m4.id: True, self.m5.id: True}
        )
        routes.append(r7)
        self.update_scores()
        
        # 路線8: M3, M5完成（一般組1人，客製化組1人）
        r8 = TestDataFactory.create_route(
            self.room, name="路線8", grade="V8",
            member_completions={self.m3.id: True, self.m5.id: True}
        )
        routes.append(r8)
        self.update_scores()
        
        # 路線9: M1, M2, M3完成（一般組3人完成）
        r9 = TestDataFactory.create_route(
            self.room, name="路線9", grade="V9",
            member_completions={self.m1.id: True, self.m2.id: True, self.m3.id: True}
        )
        routes.append(r9)
        self.update_scores()
        
        # 路線10: M4完成（客製化組1人完成）
        r10 = TestDataFactory.create_route(
            self.room, name="路線10", grade="V10",
            member_completions={self.m4.id: True}
        )
        routes.append(r10)
        self.update_scores()
        
        # 驗證分數
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.m4.refresh_from_db()
        self.m5.refresh_from_db()
        
        # M1 (一般組): 路線1(6/2=3) + 路線2(6/2=3) + 路線4(6/1=6) + 路線6(6/1=6) + 路線9(6/3=2) = 20分
        # M2 (一般組): 路線1(6/2=3) + 路線3(6/2=3) + 路線7(6/1=6) + 路線9(6/3=2) = 14分
        # M3 (一般組): 路線2(6/2=3) + 路線3(6/2=3) + 路線8(6/1=6) + 路線9(6/3=2) = 14分
        # M4 (客製化組): 路線5(6) + 路線6(6) + 路線7(6) + 路線10(6) = 24分
        # M5 (客製化組): 路線5(6) + 路線7(6) + 路線8(6) = 18分
        
        self.assertEqual(float(self.m1.total_score), 20.00)
        self.assertEqual(float(self.m2.total_score), 14.00)
        self.assertEqual(float(self.m3.total_score), 14.00)
        self.assertEqual(float(self.m4.total_score), 24.00)
        self.assertEqual(float(self.m5.total_score), 18.00)
        
        # 步驟3: 刪除部分成員，計算分數
        # 刪除 M3（一般組成員）
        self.m3.delete()
        self.update_scores()
        
        # 驗證 L 值變化：現在只有2個一般組成員（M1, M2），L = LCM(1,2) = 2
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 2)  # LCM(1,2) = 2
        
        # 重新計算分數（L從6變為2）
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m4.refresh_from_db()
        self.m5.refresh_from_db()
        
        # M1 (一般組): 路線1(2/2=1) + 路線2(2/1=2) + 路線4(2/1=2) + 路線6(2/1=2) + 路線9(2/2=1) = 8分
        # M2 (一般組): 路線1(2/2=1) + 路線3(2/1=2) + 路線7(2/1=2) + 路線9(2/2=1) = 6分
        # M4 (客製化組): 路線5(2) + 路線6(2) + 路線7(2) + 路線10(2) = 8分
        # M5 (客製化組): 路線5(2) + 路線7(2) + 路線8(2) = 6分
        
        self.assertEqual(float(self.m1.total_score), 8.00)
        self.assertEqual(float(self.m2.total_score), 6.00)
        self.assertEqual(float(self.m4.total_score), 8.00)
        self.assertEqual(float(self.m5.total_score), 6.00)
        
        # 步驟4: 刪除部分路線，計算分數
        # 刪除路線2、路線5、路線9
        r2.delete()
        r5.delete()
        r9.delete()
        routes.remove(r2)
        routes.remove(r5)
        routes.remove(r9)
        self.update_scores()
        
        # 重新計算分數
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m4.refresh_from_db()
        self.m5.refresh_from_db()
        
        # M1 (一般組): 路線1(2/2=1) + 路線4(2/1=2) + 路線6(2/1=2) = 5分
        # M2 (一般組): 路線1(2/2=1) + 路線3(2/1=2) + 路線7(2/1=2) = 5分
        # M4 (客製化組): 路線6(2) + 路線7(2) + 路線10(2) = 6分
        # M5 (客製化組): 路線7(2) + 路線8(2) = 4分
        
        self.assertEqual(float(self.m1.total_score), 5.00)
        self.assertEqual(float(self.m2.total_score), 5.00)
        self.assertEqual(float(self.m4.total_score), 6.00)
        self.assertEqual(float(self.m5.total_score), 4.00)
        
        # 步驟5: 新增部分成員到8人，計算分數
        # 現在有4個成員（M1, M2, M4, M5），需要新增4個成員到8人
        # 新增3個一般組成員和1個客製化組成員
        m6, m7, m8 = TestDataFactory.create_normal_members(
            self.room,
            count=3,
            names=["一般組4", "一般組5", "一般組6"]
        )
        m9 = TestDataFactory.create_custom_members(
            self.room,
            count=1,
            names=["客製化3"]
        )[0]
        
        # 為新成員創建成績記錄（所有路線都未完成）
        for route in routes:
            Score.objects.create(member=m6, route=route, is_completed=False)
            Score.objects.create(member=m7, route=route, is_completed=False)
            Score.objects.create(member=m8, route=route, is_completed=False)
            Score.objects.create(member=m9, route=route, is_completed=False)
        
        self.update_scores()
        
        # 驗證 L 值變化：現在有5個一般組成員（M1, M2, M6, M7, M8），L = LCM(1,2,3,4,5) = 60
        # 但由於一般組成員數 < 8，所以 L = LCM(1,2,3,4,5) = 60
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 60)  # LCM(1,2,3,4,5) = 60
        
        # 重新計算分數（L從2變為60）
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m4.refresh_from_db()
        self.m5.refresh_from_db()
        
        # M1 (一般組): 路線1(60/2=30) + 路線4(60/1=60) + 路線6(60/1=60) = 150分
        # M2 (一般組): 路線1(60/2=30) + 路線3(60/1=60) + 路線7(60/1=60) = 150分
        # M4 (客製化組): 路線6(60) + 路線7(60) + 路線10(60) = 180分
        # M5 (客製化組): 路線7(60) + 路線8(60) = 120分
        
        self.assertEqual(float(self.m1.total_score), 150.00)
        self.assertEqual(float(self.m2.total_score), 150.00)
        self.assertEqual(float(self.m4.total_score), 180.00)
        self.assertEqual(float(self.m5.total_score), 120.00)
        
        # 步驟6: 新增路線，計算分數
        # 新增路線11: M1, M6, M7完成（一般組3人完成）
        r11 = TestDataFactory.create_route(
            self.room, name="路線11", grade="V11",
            member_completions={self.m1.id: True, m6.id: True, m7.id: True}
        )
        self.update_scores()
        
        # 重新計算分數
        self.m1.refresh_from_db()
        m6.refresh_from_db()
        m7.refresh_from_db()
        
        # M1 (一般組): 150 + 路線11(60/3=20) = 170分
        # M6 (一般組): 0 + 路線11(60/3=20) = 20分
        # M7 (一般組): 0 + 路線11(60/3=20) = 20分
        
        self.assertEqual(float(self.m1.total_score), 170.00)
        self.assertEqual(float(m6.total_score), 20.00)
        self.assertEqual(float(m7.total_score), 20.00)
    
    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

