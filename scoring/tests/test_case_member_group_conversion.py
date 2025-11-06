"""
測項1：成員組別轉換測試

測試場景：
1. 建立一般組成員
2. 新增數條路線
3. 將部分一般組成員調整為客製化組
4. 驗證分數
5. 將部分成員類別調整
6. 再驗證一次分數
"""
from django.test import TestCase
from scoring.models import Room, Member, Route, Score, update_scores
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data


class TestCaseMemberGroupConversion(TestCase):
    """測項1：成員組別轉換測試"""

    def setUp(self):
        """設置測試數據"""
        self.room = TestDataFactory.create_room(name="測試房間")
        # 創建4個一般組成員
        self.m1, self.m2, self.m3, self.m4 = TestDataFactory.create_normal_members(
            self.room,
            count=4,
            names=["成員1", "成員2", "成員3", "成員4"]
        )
        # 創建成員後需要更新分數以計算L值
        self.update_scores()

    def update_scores(self):
        """更新分數"""
        update_scores(self.room.id)

    def test_member_group_conversion(self):
        """測項1：成員組別轉換完整測試"""
        # 4個一般組成員，L = LCM(1,2,3,4) = 12
        
        # 步驟1: 建立一般組成員（已在setUp中完成）
        # 驗證初始狀態
        self.assertEqual(self.m1.is_custom_calc, False)
        self.assertEqual(self.m2.is_custom_calc, False)
        self.assertEqual(self.m3.is_custom_calc, False)
        self.assertEqual(self.m4.is_custom_calc, False)
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 12)  # LCM(1,2,3,4) = 12
        
        # 步驟2: 新增數條路線
        # 路線1: M1, M2 完成（2人完成）
        r1 = TestDataFactory.create_route(
            self.room, name="路線1", grade="V3",
            member_completions={self.m1.id: True, self.m2.id: True}
        )
        self.update_scores()
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        # 完成人數=2，每人得 12/2 = 6分
        self.assertEqual(float(self.m1.total_score), 6.00)
        self.assertEqual(float(self.m2.total_score), 6.00)
        
        # 路線2: M1, M3 完成（2人完成）
        r2 = TestDataFactory.create_route(
            self.room, name="路線2", grade="V4",
            member_completions={self.m1.id: True, self.m3.id: True}
        )
        self.update_scores()
        self.m1.refresh_from_db()
        self.m3.refresh_from_db()
        # M1: 6 + 6 = 12分, M3: 0 + 6 = 6分
        self.assertEqual(float(self.m1.total_score), 12.00)
        self.assertEqual(float(self.m3.total_score), 6.00)
        
        # 路線3: M2, M3, M4 完成（3人完成）
        r3 = TestDataFactory.create_route(
            self.room, name="路線3", grade="V5",
            member_completions={self.m2.id: True, self.m3.id: True, self.m4.id: True}
        )
        self.update_scores()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.m4.refresh_from_db()
        # 完成人數=3，每人得 12/3 = 4分
        # M2: 6 + 4 = 10分, M3: 6 + 4 = 10分, M4: 0 + 4 = 4分
        self.assertEqual(float(self.m2.total_score), 10.00)
        self.assertEqual(float(self.m3.total_score), 10.00)
        self.assertEqual(float(self.m4.total_score), 4.00)
        
        # 步驟3: 將部分一般組成員調整為客製化組
        # 將 M2 和 M3 調整為客製化組
        self.m2.is_custom_calc = True
        self.m2.save()
        self.m3.is_custom_calc = True
        self.m3.save()
        
        # 更新分數
        self.update_scores()
        
        # 驗證 L 值變化：現在只有2個一般組成員（M1, M4），L = LCM(1,2) = 2
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 2)  # LCM(1,2) = 2
        
        # 步驟4: 驗證分數
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.m4.refresh_from_db()
        
        # M1 (一般組): 路線1完成(2/2=1分) + 路線2完成(2/2=1分) = 2分
        # M2 (客製化組): 完成2條路線，每條2分 = 4分
        # M3 (客製化組): 完成2條路線，每條2分 = 4分
        # M4 (一般組): 路線3完成(2/3≈0.67分) = 0.67分
        # 注意：由於一般組成員數變為2，路線1和路線2的完成人數需要重新計算
        # 路線1: M1, M2完成，但M2是客製化組，所以一般組只有M1完成，M1得2/1=2分
        # 路線2: M1, M3完成，但M3是客製化組，所以一般組只有M1完成，M1得2/1=2分
        # 路線3: M2, M3, M4完成，但M2和M3是客製化組，所以一般組只有M4完成，M4得2/1=2分
        
        # 重新計算：一般組完成人數只計算一般組成員
        # 路線1: 一般組完成人數=1（M1），M1得2/1=2分
        # 路線2: 一般組完成人數=1（M1），M1得2/1=2分
        # 路線3: 一般組完成人數=1（M4），M4得2/1=2分
        self.assertEqual(float(self.m1.total_score), 4.00)  # 2 + 2 = 4分
        
        # 客製化組：每完成一條路線得L分（現在L=2）
        # M2完成路線1和路線3，共2條，得2*2=4分
        # M3完成路線2和路線3，共2條，得2*2=4分
        self.assertEqual(float(self.m2.total_score), 4.00)  # 2條路線 * 2分 = 4分
        self.assertEqual(float(self.m3.total_score), 4.00)  # 2條路線 * 2分 = 4分
        self.assertEqual(float(self.m4.total_score), 2.00)  # 1條路線，2/1=2分
        
        # 步驟5: 將部分成員類別調整
        # 將 M2 調整回一般組，將 M1 調整為客製化組
        self.m2.is_custom_calc = False
        self.m2.save()
        self.m1.is_custom_calc = True
        self.m1.save()
        
        # 更新分數
        self.update_scores()
        
        # 驗證 L 值變化：現在有2個一般組成員（M2, M4），L = LCM(1,2) = 2
        self.room.refresh_from_db()
        self.assertEqual(self.room.standard_line_score, 2)  # LCM(1,2) = 2
        
        # 步驟6: 再驗證一次分數
        self.m1.refresh_from_db()
        self.m2.refresh_from_db()
        self.m3.refresh_from_db()
        self.m4.refresh_from_db()
        
        # M1 (客製化組): 完成路線1和路線2，共2條，得2*2=4分
        # M2 (一般組): 路線1完成(2/1=2分) + 路線3完成(2/1=2分) = 4分
        # M3 (客製化組): 完成路線2和路線3，共2條，得2*2=4分
        # M4 (一般組): 路線3完成(2/1=2分) = 2分
        
        # 重新計算一般組完成人數：
        # 路線1: 一般組完成人數=1（M2），M2得2/1=2分
        # 路線2: 一般組完成人數=0，無一般組成員完成
        # 路線3: 一般組完成人數=2（M2, M4），每人得2/2=1分
        
        self.assertEqual(float(self.m1.total_score), 4.00)  # 客製化組：2條路線 * 2分 = 4分
        self.assertEqual(float(self.m2.total_score), 3.00)  # 一般組：2 + 1 = 3分
        self.assertEqual(float(self.m3.total_score), 4.00)  # 客製化組：2條路線 * 2分 = 4分
        self.assertEqual(float(self.m4.total_score), 1.00)  # 一般組：1分
    
    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

