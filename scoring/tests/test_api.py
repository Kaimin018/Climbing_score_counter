from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data, create_basic_test_setup


class APITestCase(TestCase):
    """測試 API 接口"""

    def setUp(self):
        self.client = APIClient()
        self.room = TestDataFactory.create_room(name="API測試房間", standard_line_score=12)
        self.m1 = TestDataFactory.create_normal_members(self.room, count=1, names=["測試成員1"])[0]
        self.m2 = TestDataFactory.create_normal_members(self.room, count=1, names=["測試成員2"])[0]
    
    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

    def test_get_leaderboard(self):
        """測試獲取排行榜"""
        url = f'/api/rooms/{self.room.id}/leaderboard/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('room_info', response.data)
        self.assertIn('leaderboard', response.data)

    def test_create_route(self):
        """測試創建路線"""
        url = f'/api/rooms/{self.room.id}/routes/'
        data = {
            'name': '測試路線',
            'grade': 'V4',
            'photo_url': '',
            'member_completions': {
                str(self.m1.id): True,
                str(self.m2.id): False
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Route.objects.count(), 1)
        self.assertEqual(Score.objects.count(), 2)

    def test_update_score(self):
        """測試更新成績"""
        route = Route.objects.create(room=self.room, name="測試路線")
        score = Score.objects.create(member=self.m1, route=route, is_completed=False)
        
        url = f'/api/scores/{score.id}/'
        data = {'is_completed': True}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        score.refresh_from_db()
        self.assertTrue(score.is_completed)

    def test_create_room_add_member_create_route(self):
        """測試完整流程：創建新房間 -> 新增成員 -> 建立新路線"""
        # 步驟 1: 創建新房間
        room_data = {
            'name': '測試房間_20250101'
        }
        response = self.client.post('/api/rooms/', room_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        room_id = response.data['id']
        test_room = Room.objects.get(id=room_id)
        
        # 驗證房間創建成功
        self.assertEqual(Room.objects.count(), 2)  # 原有1個 + 新建1個
        self.assertEqual(response.data['name'], '測試房間_20250101')
        # 驗證每一條線總分預設為1（因為還沒有一般組成員）
        self.assertEqual(response.data['standard_line_score'], 1)
        
        # 步驟 2: 在該房間新增成員
        member1_data = {
            'room': room_id,
            'name': '測試成員A',
            'is_custom_calc': False
        }
        response = self.client.post('/api/members/', member1_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member1_id = response.data['id']
        
        member2_data = {
            'room': room_id,
            'name': '測試成員B',
            'is_custom_calc': False
        }
        response = self.client.post('/api/members/', member2_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        member2_id = response.data['id']
        
        # 驗證成員創建成功
        self.assertEqual(Member.objects.filter(room_id=room_id).count(), 2)
        
        # 驗證每一條線總分自動更新（2個一般組成員，LCM(1,2) = 2）
        test_room.refresh_from_db()
        self.assertEqual(test_room.standard_line_score, 2)
        
        # 步驟 3: 建立新路線
        route_data = {
            'name': '路線1',
            'grade': 'V3',
            'member_completions': {
                str(member1_id): True,
                str(member2_id): False
            }
        }
        response = self.client.post(f'/api/rooms/{room_id}/routes/', route_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route_id = response.data['id']
        
        # 驗證路線創建成功
        self.assertEqual(Route.objects.filter(room_id=room_id).count(), 1)
        # 注意：API 返回的路線名稱不會自動加上【路線】前綴（這是前端處理的）
        # 但路線名稱應該正確保存
        self.assertEqual(response.data['name'], '路線1')
        
        # 驗證成績記錄創建成功
        self.assertEqual(Score.objects.filter(route_id=route_id).count(), 2)
        
        # 驗證完成狀態正確
        score1 = Score.objects.get(member_id=member1_id, route_id=route_id)
        score2 = Score.objects.get(member_id=member2_id, route_id=route_id)
        self.assertTrue(score1.is_completed)
        self.assertFalse(score2.is_completed)
        
        # 驗證分數計算正確（L=2, 1人完成，每人獲得2分）
        member1 = Member.objects.get(id=member1_id)
        member1.refresh_from_db()
        self.assertEqual(float(member1.total_score), 2.00)
        
        member2 = Member.objects.get(id=member2_id)
        member2.refresh_from_db()
        self.assertEqual(float(member2.total_score), 0.00)
        
        # 測試完成後清理新創建的房間
        cleanup_test_data(room=test_room)

    def test_create_route_with_initial_completions(self):
        """測試創建路線時勾選完成成員，驗證完成人數正確顯示"""
        # 創建一個房間和兩個一般組成員
        room = Room.objects.create(name="測試房間")
        m1 = Member.objects.create(room=room, name="成員1", is_custom_calc=False)
        m2 = Member.objects.create(room=room, name="成員2", is_custom_calc=False)
        m3 = Member.objects.create(room=room, name="成員3", is_custom_calc=True)  # 客製化組
        
        # 創建路線，勾選兩個一般組成員為完成
        url = f'/api/rooms/{room.id}/routes/'
        route_data = {
            'name': '路線1',
            'grade': 'V5',
            'member_completions': {
                str(m1.id): True,
                str(m2.id): True,
                str(m3.id): False
            }
        }
        response = self.client.post(url, route_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 驗證 API 響應中的 scores 數據
        self.assertIn('scores', response.data)
        scores = response.data['scores']
        
        # 應該有 3 個 score 記錄（對應 3 個成員）
        self.assertEqual(len(scores), 3)
        
        # 統計完成人數（一般組成員且 is_completed=True）
        completed_scores = [s for s in scores if s['is_completed']]
        # 應該有 2 個完成（m1 和 m2）
        self.assertEqual(len(completed_scores), 2, 
                        f"完成人數應該是 2，但實際是 {len(completed_scores)}。scores: {scores}")
        
        # 驗證數據庫中的狀態
        route = Route.objects.get(id=response.data['id'])
        route.refresh_from_db()
        
        # 驗證 scores 關聯
        db_scores = route.scores.all()
        self.assertEqual(db_scores.count(), 3)
        
        # 驗證完成狀態
        score_m1 = Score.objects.get(member=m1, route=route)
        score_m2 = Score.objects.get(member=m2, route=route)
        score_m3 = Score.objects.get(member=m3, route=route)
        self.assertTrue(score_m1.is_completed, "成員1應該標記為完成")
        self.assertTrue(score_m2.is_completed, "成員2應該標記為完成")
        self.assertFalse(score_m3.is_completed, "成員3應該標記為未完成")
        
        # 驗證一般組完成人數（normal_completers）
        normal_completers = Score.objects.filter(
            route=route,
            is_completed=True,
            member__is_custom_calc=False
        ).count()
        self.assertEqual(normal_completers, 2, 
                        f"一般組完成人數應該是 2，但實際是 {normal_completers}")
        
        # 測試完成後清理房間
        cleanup_test_data(room=room)

    def test_get_room_with_routes_shows_completion_count(self):
        """測試通過 GET /api/rooms/{id}/ 獲取房間時，routes 的完成人數正確顯示"""
        # 創建一個房間和兩個一般組成員
        room = Room.objects.create(name="測試房間")
        m1 = Member.objects.create(room=room, name="成員1", is_custom_calc=False)
        m2 = Member.objects.create(room=room, name="成員2", is_custom_calc=False)
        m3 = Member.objects.create(room=room, name="成員3", is_custom_calc=True)  # 客製化組
        
        # 創建路線，勾選兩個一般組成員為完成
        url = f'/api/rooms/{room.id}/routes/'
        route_data = {
            'name': '路線1',
            'grade': 'V5',
            'member_completions': {
                str(m1.id): True,
                str(m2.id): True,
                str(m3.id): False
            }
        }
        response = self.client.post(url, route_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route_id = response.data['id']
        
        # 通過 GET /api/rooms/{id}/ 獲取房間數據
        room_url = f'/api/rooms/{room.id}/'
        room_response = self.client.get(room_url)
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        
        # 驗證房間數據中包含 routes
        self.assertIn('routes', room_response.data)
        routes = room_response.data['routes']
        self.assertEqual(len(routes), 1, "應該有 1 條路線")
        
        # 找到剛創建的路線
        created_route = None
        for route in routes:
            if route['id'] == route_id:
                created_route = route
                break
        
        self.assertIsNotNone(created_route, "應該找到剛創建的路線")
        
        # 驗證路線的 scores 數據
        self.assertIn('scores', created_route, "路線應該包含 scores 數據")
        scores = created_route['scores']
        self.assertEqual(len(scores), 3, "應該有 3 個 score 記錄（對應 3 個成員）")
        
        # 統計完成人數（is_completed=True）
        completed_scores = [s for s in scores if s['is_completed']]
        self.assertEqual(len(completed_scores), 2, 
                        f"完成人數應該是 2，但實際是 {len(completed_scores)}。scores: {scores}")
        
        # 驗證前端計算的完成人數（所有完成的人）
        # 前端代碼：const completedCount = route.scores ? route.scores.filter(s => s.is_completed).length : 0;
        # 這應該返回 2（m1 和 m2 都完成了）
        frontend_completed_count = len(completed_scores)
        self.assertEqual(frontend_completed_count, 2,
                        f"前端計算的完成人數應該是 2，但實際是 {frontend_completed_count}")
        
        # 測試完成後清理房間
        cleanup_test_data(room=room)

    def test_create_route_with_multiple_completions_frontend_display(self):
        """測試新建立路線時選擇多個完成人員，驗證前端顯示的完成人數正確"""
        # 創建一個房間和多個成員（5個一般組成員 + 1個客製化組成員）
        room = Room.objects.create(name="測試房間")
        m1 = Member.objects.create(room=room, name="成員1", is_custom_calc=False)
        m2 = Member.objects.create(room=room, name="成員2", is_custom_calc=False)
        m3 = Member.objects.create(room=room, name="成員3", is_custom_calc=False)
        m4 = Member.objects.create(room=room, name="成員4", is_custom_calc=False)
        m5 = Member.objects.create(room=room, name="成員5", is_custom_calc=False)
        m6 = Member.objects.create(room=room, name="成員6", is_custom_calc=True)  # 客製化組
        
        # 創建路線，勾選4個一般組成員為完成（m1, m2, m3, m4），m5 和 m6 未完成
        url = f'/api/rooms/{room.id}/routes/'
        route_data = {
            'name': '路線測試多完成',
            'grade': 'V6',
            'member_completions': {
                str(m1.id): True,
                str(m2.id): True,
                str(m3.id): True,
                str(m4.id): True,
                str(m5.id): False,
                str(m6.id): False
            }
        }
        response = self.client.post(url, route_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        route_id = response.data['id']
        
        # 驗證創建路線的 API 響應中 scores 數據正確
        self.assertIn('scores', response.data)
        scores = response.data['scores']
        self.assertEqual(len(scores), 6, "應該有 6 個 score 記錄（對應 6 個成員）")
        
        # 統計完成人數
        completed_scores = [s for s in scores if s['is_completed']]
        self.assertEqual(len(completed_scores), 4, 
                        f"創建路線 API 響應中完成人數應該是 4，但實際是 {len(completed_scores)}。scores: {scores}")
        
        # 通過 GET /api/rooms/{id}/ 獲取房間數據（模擬前端刷新）
        room_url = f'/api/rooms/{room.id}/'
        room_response = self.client.get(room_url)
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        
        # 驗證房間數據中包含 routes
        self.assertIn('routes', room_response.data)
        routes = room_response.data['routes']
        self.assertEqual(len(routes), 1, "應該有 1 條路線")
        
        # 找到剛創建的路線
        created_route = None
        for route in routes:
            if route['id'] == route_id:
                created_route = route
                break
        
        self.assertIsNotNone(created_route, "應該找到剛創建的路線")
        
        # 驗證路線的 scores 數據
        self.assertIn('scores', created_route, "路線應該包含 scores 數據")
        route_scores = created_route['scores']
        self.assertEqual(len(route_scores), 6, "應該有 6 個 score 記錄（對應 6 個成員）")
        
        # 統計完成人數（is_completed=True）
        completed_scores_from_room = [s for s in route_scores if s['is_completed']]
        self.assertEqual(len(completed_scores_from_room), 4, 
                        f"完成人數應該是 4，但實際是 {len(completed_scores_from_room)}。scores: {route_scores}")
        
        # 驗證前端計算的完成人數（模擬前端代碼邏輯）
        # 前端代碼：const completedCount = route.scores ? route.scores.filter(s => s.is_completed).length : 0;
        # 這應該返回 4（m1, m2, m3, m4 都完成了）
        frontend_completed_count = len(completed_scores_from_room)
        self.assertEqual(frontend_completed_count, 4,
                        f"前端計算的完成人數應該是 4，但實際是 {frontend_completed_count}")
        
        # 驗證總人數（前端代碼：const totalCount = route.scores ? route.scores.length : 0;）
        frontend_total_count = len(route_scores)
        self.assertEqual(frontend_total_count, 6,
                        f"前端計算的總人數應該是 6，但實際是 {frontend_total_count}")
        
        # 驗證前端顯示格式：完成: ${completedCount}/${totalCount} 人
        # 應該是 "完成: 4/6 人"
        expected_display = f"完成: {frontend_completed_count}/{frontend_total_count} 人"
        self.assertEqual(expected_display, "完成: 4/6 人",
                        f"前端顯示格式應該是 '完成: 4/6 人'，但實際是 '{expected_display}'")
        
        # 驗證數據庫中的狀態
        route = Route.objects.get(id=route_id)
        route.refresh_from_db()
        
        # 驗證完成狀態
        self.assertTrue(Score.objects.get(member=m1, route=route).is_completed, "成員1應該標記為完成")
        self.assertTrue(Score.objects.get(member=m2, route=route).is_completed, "成員2應該標記為完成")
        self.assertTrue(Score.objects.get(member=m3, route=route).is_completed, "成員3應該標記為完成")
        self.assertTrue(Score.objects.get(member=m4, route=route).is_completed, "成員4應該標記為完成")
        self.assertFalse(Score.objects.get(member=m5, route=route).is_completed, "成員5應該標記為未完成")
        self.assertFalse(Score.objects.get(member=m6, route=route).is_completed, "成員6應該標記為未完成")
        
        # 測試完成後清理房間
        cleanup_test_data(room=room)

    def test_create_route_immediate_refresh_simulation(self):
        """深度測試：模擬前端完整流程 - 創建路線後立即刷新獲取房間數據"""
        # 創建一個房間和多個成員（模擬實際使用場景）
        room = Room.objects.create(name="既有房間測試")
        m1 = Member.objects.create(room=room, name="成員A", is_custom_calc=False)
        m2 = Member.objects.create(room=room, name="成員B", is_custom_calc=False)
        m3 = Member.objects.create(room=room, name="成員C", is_custom_calc=False)
        m4 = Member.objects.create(room=room, name="成員D", is_custom_calc=True)  # 客製化組
        
        # 步驟 1: 創建路線，勾選3個一般組成員為完成（模擬前端 FormData 提交）
        url = f'/api/rooms/{room.id}/routes/'
        route_data = {
            'name': '路線新建測試',
            'grade': 'V4',
            'member_completions': {
                str(m1.id): True,
                str(m2.id): True,
                str(m3.id): True,
                str(m4.id): False
            }
        }
        
        # 創建路線（模擬前端 POST 請求）
        create_response = self.client.post(url, route_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        route_id = create_response.data['id']
        
        # 驗證創建響應中的 scores 數據
        self.assertIn('scores', create_response.data)
        create_scores = create_response.data['scores']
        self.assertEqual(len(create_scores), 4, "創建響應應該有 4 個 score 記錄")
        create_completed = [s for s in create_scores if s['is_completed']]
        self.assertEqual(len(create_completed), 3, 
                       f"創建響應中完成人數應該是 3，但實際是 {len(create_completed)}")
        
        # 步驟 2: 立即獲取房間數據（模擬前端 refreshLeaderboard() -> loadRoutes()）
        # 這是最關鍵的測試點 - 前端在創建路線後立即調用 GET /api/rooms/{id}/
        room_url = f'/api/rooms/{room.id}/'
        room_response = self.client.get(room_url)
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        
        # 驗證房間數據
        self.assertIn('routes', room_response.data)
        routes = room_response.data['routes']
        self.assertGreater(len(routes), 0, "應該至少有一條路線")
        
        # 找到剛創建的路線
        created_route = None
        for route in routes:
            if route['id'] == route_id:
                created_route = route
                break
        
        self.assertIsNotNone(created_route, f"應該找到剛創建的路線 (ID: {route_id})")
        
        # 關鍵驗證：檢查 scores 數據是否存在且完整
        self.assertIn('scores', created_route, 
                     f"路線應該包含 scores 數據。路線數據: {created_route}")
        
        route_scores = created_route['scores']
        self.assertIsNotNone(route_scores, "scores 不應該為 None")
        self.assertIsInstance(route_scores, list, f"scores 應該是列表類型，實際是 {type(route_scores)}")
        self.assertEqual(len(route_scores), 4, 
                       f"應該有 4 個 score 記錄，但實際是 {len(route_scores)}。scores: {route_scores}")
        
        # 統計完成人數（模擬前端計算邏輯）
        completed_scores = [s for s in route_scores if s.get('is_completed', False)]
        self.assertEqual(len(completed_scores), 3, 
                       f"完成人數應該是 3，但實際是 {len(completed_scores)}。scores: {route_scores}")
        
        # 驗證前端顯示邏輯（模擬 displayRoutes 函數）
        completed_count = len(completed_scores)
        total_count = len(route_scores)
        display_text = f"完成: {completed_count}/{total_count} 人"
        self.assertEqual(display_text, "完成: 3/4 人",
                       f"前端顯示應該是 '完成: 3/4 人'，但實際是 '{display_text}'")
        
        # 步驟 3: 再次驗證數據庫狀態（確保數據持久化正確）
        route = Route.objects.get(id=route_id)
        db_scores = route.scores.all()
        self.assertEqual(db_scores.count(), 4)
        
        db_completed = db_scores.filter(is_completed=True)
        self.assertEqual(db_completed.count(), 3, "數據庫中完成人數應該是 3")
        
        # 步驟 4: 驗證數據一致性（API 返回的數據應該與數據庫一致）
        for score_data in route_scores:
            member_id = score_data.get('member_id')
            is_completed = score_data.get('is_completed', False)
            
            # 從數據庫驗證
            try:
                db_score = Score.objects.get(member_id=member_id, route_id=route_id)
                self.assertEqual(db_score.is_completed, is_completed,
                               f"成員 {member_id} 的完成狀態不一致：API={is_completed}, DB={db_score.is_completed}")
            except Score.DoesNotExist:
                self.fail(f"數據庫中找不到成員 {member_id} 的 score 記錄")
        
        # 測試完成後清理房間
        cleanup_test_data(room=room)

    def test_create_route_deep_dive_complete_flow(self):
        """深度分析：完整追蹤創建路線的整個流程"""
        # 創建測試環境
        room = Room.objects.create(name="深度分析測試房間")
        m1 = Member.objects.create(room=room, name="成員甲", is_custom_calc=False)
        m2 = Member.objects.create(room=room, name="成員乙", is_custom_calc=False)
        m3 = Member.objects.create(room=room, name="成員丙", is_custom_calc=False)
        
        # 步驟 1: 模擬前端 FormData 提交（勾選 m1 和 m2）
        url = f'/api/rooms/{room.id}/routes/'
        
        # 模擬 FormData 格式（使用 multipart）
        from django.test.client import encode_multipart, BOUNDARY
        route_data = {
            'name': '深度測試路線',
            'grade': 'V5',
            'member_completions': '{"' + str(m1.id) + '":true,"' + str(m2.id) + '":true,"' + str(m3.id) + '":false}'
        }
        
        # 步驟 2: 創建路線（POST 請求）
        response = self.client.post(url, route_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, 
                        f"創建路線失敗: {response.data}")
        
        route_id = response.data['id']
        
        # 步驟 3: 驗證創建響應
        create_response_scores = response.data.get('scores', [])
        self.assertEqual(len(create_response_scores), 3, 
                        f"創建響應應該有 3 個 scores，實際: {len(create_response_scores)}")
        create_completed = [s for s in create_response_scores if s.get('is_completed')]
        self.assertEqual(len(create_completed), 2,
                        f"創建響應中完成人數應該是 2，實際: {len(create_completed)}。scores: {create_response_scores}")
        
        # 步驟 4: 驗證數據庫狀態（創建後立即檢查）
        route = Route.objects.get(id=route_id)
        db_scores = route.scores.all()
        self.assertEqual(db_scores.count(), 3, "數據庫中應該有 3 個 score 記錄")
        db_completed = db_scores.filter(is_completed=True)
        self.assertEqual(db_completed.count(), 2, "數據庫中完成人數應該是 2")
        
        # 步驟 5: 立即獲取房間數據（模擬前端 refreshLeaderboard -> loadRoutes）
        # 這是最關鍵的測試點
        room_response = self.client.get(f'/api/rooms/{room.id}/')
        self.assertEqual(room_response.status_code, status.HTTP_200_OK)
        
        routes_in_room = room_response.data.get('routes', [])
        self.assertGreater(len(routes_in_room), 0, "房間應該至少有一條路線")
        
        # 找到剛創建的路線
        created_route_in_room = None
        for r in routes_in_room:
            if r['id'] == route_id:
                created_route_in_room = r
                break
        
        self.assertIsNotNone(created_route_in_room, 
                           f"應該找到剛創建的路線 (ID: {route_id})。所有路線: {[r['id'] for r in routes_in_room]}")
        
        # 關鍵驗證：檢查 scores 數據
        route_scores_in_room = created_route_in_room.get('scores', [])
        
        # 詳細驗證
        self.assertIsNotNone(route_scores_in_room, "scores 不應該是 None")
        self.assertIsInstance(route_scores_in_room, list, 
                            f"scores 應該是列表，實際是 {type(route_scores_in_room)}")
        self.assertEqual(len(route_scores_in_room), 3,
                        f"應該有 3 個 score 記錄，實際: {len(route_scores_in_room)}。scores: {route_scores_in_room}")
        
        # 統計完成人數（模擬前端計算）
        completed_in_room = [s for s in route_scores_in_room if s.get('is_completed', False)]
        self.assertEqual(len(completed_in_room), 2,
                        f"完成人數應該是 2，實際: {len(completed_in_room)}。所有 scores: {route_scores_in_room}")
        
        # 步驟 6: 驗證前端顯示邏輯
        frontend_completed = len(completed_in_room)
        frontend_total = len(route_scores_in_room)
        display_text = f"完成: {frontend_completed}/{frontend_total} 人"
        self.assertEqual(display_text, "完成: 2/3 人",
                       f"前端顯示應該是 '完成: 2/3 人'，實際: '{display_text}'")
        
        # 步驟 7: 驗證數據一致性（所有步驟的數據應該一致）
        # 創建響應的完成人數
        create_completed_count = len(create_completed)
        # 數據庫的完成人數
        db_completed_count = db_completed.count()
        # 房間響應的完成人數
        room_completed_count = len(completed_in_room)
        
        self.assertEqual(create_completed_count, db_completed_count, 
                        "創建響應和數據庫的完成人數應該一致")
        self.assertEqual(db_completed_count, room_completed_count,
                        "數據庫和房間響應的完成人數應該一致")
        self.assertEqual(create_completed_count, room_completed_count,
                        "創建響應和房間響應的完成人數應該一致")
        
        # 步驟 8: 驗證每個成員的完成狀態
        for score_data in route_scores_in_room:
            member_id = score_data.get('member_id')
            is_completed_api = score_data.get('is_completed', False)
            
            # 從數據庫驗證
            db_score = Score.objects.get(member_id=member_id, route_id=route_id)
            self.assertEqual(db_score.is_completed, is_completed_api,
                           f"成員 {member_id} 的完成狀態不一致：API={is_completed_api}, DB={db_score.is_completed}")
        
        # 測試完成後清理房間
        cleanup_test_data(room=room)

