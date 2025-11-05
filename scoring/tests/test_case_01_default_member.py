from django.test import TestCase
from scoring.models import Room, Member, Route, Score, update_scores


class TestCase1To10(TestCase):
    """測試案例 1-10：循序漸進新增路線（所有成員為一般組）"""

    def setUp(self):
        """設置測試數據"""
        self.room = Room.objects.create(name="測試房間")
        # 所有成員都設置為非客製化組（一般組）
        self.m1 = Member.objects.create(room=self.room, name="王小明", is_custom_calc=False)
        self.m2 = Member.objects.create(room=self.room, name="李大華", is_custom_calc=False)
        self.m3 = Member.objects.create(room=self.room, name="張三", is_custom_calc=False)
        self.m4 = Member.objects.create(room=self.room, name="陳四", is_custom_calc=False)

    def update_scores(self):
        """更新分數"""
        update_scores(self.room.id)

    def test_case_1_to_10(self):
        """測試案例 1-10：循序漸進新增路線"""
        # 4個一般組成員，L = LCM(1,2,3,4) = 12

        # 案例 1: R1 (Green V2) - M1, M3 完成（2人完成）
        r1 = Route.objects.create(room=self.room, name="R1", grade="Green V2")
        Score.objects.create(member=self.m1, route=r1, is_completed=True)
        Score.objects.create(member=self.m2, route=r1, is_completed=False)
        Score.objects.create(member=self.m3, route=r1, is_completed=True)
        Score.objects.create(member=self.m4, route=r1, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 6.00)
        self.assertEqual(float(self.m3.total_score), 6.00)

        # 案例 2: R2 (Blue V4) - M2, M3 完成（2人完成）
        r2 = Route.objects.create(room=self.room, name="R2", grade="Blue V4")
        Score.objects.create(member=self.m1, route=r2, is_completed=False)
        Score.objects.create(member=self.m2, route=r2, is_completed=True)
        Score.objects.create(member=self.m3, route=r2, is_completed=True)
        Score.objects.create(member=self.m4, route=r2, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 6.00)  # 不變
        self.assertEqual(float(self.m2.total_score), 6.00)  # 0 + 6
        self.assertEqual(float(self.m3.total_score), 12.00)  # 6 + 6

        # 案例 3: R3 (Red V4) - M1, M2 完成（2人完成）
        r3 = Route.objects.create(room=self.room, name="R3", grade="Red V4")
        Score.objects.create(member=self.m1, route=r3, is_completed=True)
        Score.objects.create(member=self.m2, route=r3, is_completed=True)
        Score.objects.create(member=self.m3, route=r3, is_completed=False)
        Score.objects.create(member=self.m4, route=r3, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 12.00)  # 6 + 6
        self.assertEqual(float(self.m2.total_score), 12.00)  # 6 + 6

        # 案例 4: R4 (Yellow V6) - M1, M2 完成（2人完成）
        r4 = Route.objects.create(room=self.room, name="R4", grade="Yellow V6")
        Score.objects.create(member=self.m1, route=r4, is_completed=True)
        Score.objects.create(member=self.m2, route=r4, is_completed=True)
        Score.objects.create(member=self.m3, route=r4, is_completed=False)
        Score.objects.create(member=self.m4, route=r4, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 18.00)  # 12 + 6
        self.assertEqual(float(self.m2.total_score), 18.00)  # 12 + 6

        # 案例 5: R5 (Black V7) - 僅 M3 完成（1人完成）
        r5 = Route.objects.create(room=self.room, name="R5", grade="Black V7")
        Score.objects.create(member=self.m1, route=r5, is_completed=False)
        Score.objects.create(member=self.m2, route=r5, is_completed=False)
        Score.objects.create(member=self.m3, route=r5, is_completed=True)
        Score.objects.create(member=self.m4, route=r5, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=1，每人得 12/1 = 12分
        self.assertEqual(float(self.m1.total_score), 18.00)  # 不變
        self.assertEqual(float(self.m2.total_score), 18.00)  # 不變
        self.assertEqual(float(self.m3.total_score), 24.00)  # 12 + 12

        # 案例 7: R7 (Pink V3) - M1, M2 完成（2人完成）
        r7 = Route.objects.create(room=self.room, name="R7", grade="Pink V3")
        Score.objects.create(member=self.m1, route=r7, is_completed=True)
        Score.objects.create(member=self.m2, route=r7, is_completed=True)
        Score.objects.create(member=self.m3, route=r7, is_completed=False)
        Score.objects.create(member=self.m4, route=r7, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 24.00)  # 18 + 6
        self.assertEqual(float(self.m2.total_score), 24.00)  # 18 + 6

        # 案例 8: R8 (Brown V8) - M2, M3 完成（2人完成）
        r8 = Route.objects.create(room=self.room, name="R8", grade="Brown V8")
        Score.objects.create(member=self.m1, route=r8, is_completed=False)
        Score.objects.create(member=self.m2, route=r8, is_completed=True)
        Score.objects.create(member=self.m3, route=r8, is_completed=True)
        Score.objects.create(member=self.m4, route=r8, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 24.00)  # 不變
        self.assertEqual(float(self.m2.total_score), 30.00)  # 24 + 6
        self.assertEqual(float(self.m3.total_score), 30.00)  # 24 + 6

        # 案例 9: R9 (Orange V5) - M1, M2, M3 完成（3人完成）
        r9 = Route.objects.create(room=self.room, name="R9", grade="Orange V5")
        Score.objects.create(member=self.m1, route=r9, is_completed=True)
        Score.objects.create(member=self.m2, route=r9, is_completed=True)
        Score.objects.create(member=self.m3, route=r9, is_completed=True)
        Score.objects.create(member=self.m4, route=r9, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=3，每人得 12/3 = 4分
        self.assertEqual(float(self.m1.total_score), 28.00)  # 24 + 4
        self.assertEqual(float(self.m2.total_score), 34.00)  # 30 + 4
        self.assertEqual(float(self.m3.total_score), 34.00)  # 30 + 4

        # 案例 10: R10 (White V1) - M1, M3 完成（2人完成）
        r10 = Route.objects.create(room=self.room, name="R10", grade="White V1")
        Score.objects.create(member=self.m1, route=r10, is_completed=True)
        Score.objects.create(member=self.m2, route=r10, is_completed=False)
        Score.objects.create(member=self.m3, route=r10, is_completed=True)
        Score.objects.create(member=self.m4, route=r10, is_completed=False)
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 34.00)  # 28 + 6
        self.assertEqual(float(self.m2.total_score), 34.00)  # 不變
        self.assertEqual(float(self.m3.total_score), 40.00)  # 34 + 6

