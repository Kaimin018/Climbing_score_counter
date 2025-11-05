from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data


class TestCaseRouteNameEdit(TestCase):
    """測試案例：編輯路線名稱的各種場景"""

    def setUp(self):
        self.client = APIClient()
        self.room = TestDataFactory.create_room(name="測試房間")
        self.m1, self.m2 = TestDataFactory.create_normal_members(
            self.room,
            count=2,
            names=["測試成員1", "測試成員2"]
        )
        
        # 創建測試路線並自動創建成績記錄
        self.route1 = TestDataFactory.create_route(
            room=self.room,
            name="【路線】路線1",
            grade="V3",
            members=[self.m1, self.m2]
        )
        self.route2 = TestDataFactory.create_route(
            room=self.room,
            name="【路線】123",
            grade="V4",
            members=[self.m1, self.m2]
        )
        self.route3 = TestDataFactory.create_route(
            room=self.room,
            name="【路線】正面黑",
            grade="V5",
            members=[self.m1, self.m2]
        )

    def test_edit_route_name_without_change(self):
        """測試：編輯路線但不修改名稱（應該保持原樣）"""
        url = f'/api/routes/{self.route1.id}/'
        data = {
            'name': '【路線】路線1',  # 保持原樣
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): False,
                str(self.m2.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.route1.refresh_from_db()
        self.assertEqual(self.route1.name, '【路線】路線1')

    def test_edit_route_name_change_to_number(self):
        """測試：編輯路線名稱改為數字（例如：123）"""
        url = f'/api/routes/{self.route2.id}/'
        data = {
            'name': '【路線】456',
            'grade': 'V4',
            'member_completions': {
                str(self.m1.id): False,
                str(self.m2.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.route2.refresh_from_db()
        self.assertEqual(self.route2.name, '【路線】456')

    def test_edit_route_name_change_to_text(self):
        """測試：編輯路線名稱改為文字（例如：正面黑）"""
        url = f'/api/routes/{self.route3.id}/'
        data = {
            'name': '【路線】背面白',
            'grade': 'V5',
            'member_completions': {
                str(self.m1.id): False,
                str(self.m2.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.route3.refresh_from_db()
        self.assertEqual(self.route3.name, '【路線】背面白')

    def test_edit_route_name_remove_prefix_in_request(self):
        """測試：請求中不包含【路線】前綴的情況（應該自動添加）"""
        url = f'/api/routes/{self.route1.id}/'
        data = {
            'name': '新名稱',  # 不包含【路線】前綴
            'grade': 'V3',
            'member_completions': {
                str(self.m1.id): False,
                str(self.m2.id): False
            }
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.route1.refresh_from_db()
        # 注意：後端不會自動添加前綴，所以名稱應該是 '新名稱'
        # 但前端會自動添加前綴，所以這裡測試的是後端行為
        self.assertEqual(self.route1.name, '新名稱')

    def test_retrieve_route_returns_correct_name(self):
        """測試：獲取路線詳情時，名稱應該正確返回（不應被截斷）"""
        url = f'/api/routes/{self.route1.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 驗證名稱完整返回
        self.assertEqual(response.data['name'], '【路線】路線1')
        # 驗證名稱的第一個字符是【，不是路
        self.assertTrue(response.data['name'].startswith('【路線】'))
        # 驗證名稱不應被截斷（應該包含完整的"路線1"）
        self.assertIn('路線1', response.data['name'])

    def test_retrieve_route_with_text_name(self):
        """測試：獲取包含文字的路線名稱時，名稱應該完整返回"""
        url = f'/api/routes/{self.route3.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 驗證名稱完整返回
        self.assertEqual(response.data['name'], '【路線】正面黑')
        # 驗證名稱的第一個字符是【
        self.assertTrue(response.data['name'].startswith('【路線】'))
        # 驗證完整名稱包含"正面黑"
        self.assertIn('正面黑', response.data['name'])
    
    def tearDown(self):
        """測試完成後清理數據"""
        cleanup_test_data(room=self.room)

