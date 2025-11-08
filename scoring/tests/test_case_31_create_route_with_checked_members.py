"""
創建路線時直接勾選已通過成員的測試用例

測試項目：
1. 創建路線時直接勾選成員為已完成狀態應該成功
2. 創建路線時勾選所有成員為已完成狀態應該成功
3. 創建路線時勾選部分成員為已完成狀態應該成功
4. 驗證創建後成員的完成狀態正確
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from scoring.models import Room, Member, Route, Score
from scoring.tests.test_helpers import TestDataFactory, cleanup_test_data
import json
import logging

logger = logging.getLogger(__name__)


class TestCaseCreateRouteWithCheckedMembers(TestCase):
    """測試創建路線時直接勾選已通過成員"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = APIClient()
        self.factory = TestDataFactory()
        self.room = self.factory.create_room("勾選成員測試房間")
        self.m1, self.m2, self.m3 = self.factory.create_normal_members(
            self.room,
            count=3,
            names=["成員1", "成員2", "成員3"]
        )
        self.user = User.objects.create_user(
            username="testuser",
            password="TestPass123!",
            email="test@example.com"
        )
        self.client.force_authenticate(user=self.user)
    
    def tearDown(self):
        """清理測試數據"""
        cleanup_test_data(room=self.room)
    
    def _create_route_with_member_completions(self, name, grade, member_completions, expected_status=status.HTTP_201_CREATED):
        """輔助方法：創建帶成員完成狀態的路線"""
        url = f'/api/rooms/{self.room.id}/routes/'
        
        data = {
            'name': name,
            'grade': grade,
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.post(
            url,
            data=data,
            format='json'
        )
        
        logger.info(f"{name} 創建測試 - Status: {response.status_code}")
        if hasattr(response, 'data'):
            logger.info(f"Response data: {response.data}")
        if response.status_code != expected_status:
            logger.error(f"Response content: {response.content.decode('utf-8') if response.content else 'N/A'}")
        
        return response
    
    def test_create_route_with_one_checked_member(self):
        """
        測試：創建路線時直接勾選一個成員為已完成狀態應該成功
        
        測試步驟：
        1. 創建路線，勾選成員1為已完成
        2. 驗證創建成功
        3. 驗證成員1的完成狀態為True
        4. 驗證其他成員的完成狀態為False
        """
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): False,
            str(self.m3.id): False
        }
        
        response = self._create_route_with_member_completions(
            '單成員完成路線',
            'V3',
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertFalse(score2.is_completed, "成員2應該標記為未完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_all_checked_members(self):
        """
        測試：創建路線時勾選所有成員為已完成狀態應該成功
        
        測試步驟：
        1. 創建路線，勾選所有成員為已完成
        2. 驗證創建成功
        3. 驗證所有成員的完成狀態為True
        """
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): True
        }
        
        response = self._create_route_with_member_completions(
            '全部完成路線',
            'V4',
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證所有成員的完成狀態
        for member in [self.m1, self.m2, self.m3]:
            score = Score.objects.get(member=member, route=route)
            self.assertTrue(score.is_completed, f"成員{member.id}應該標記為已完成")
    
    def test_create_route_with_partial_checked_members(self):
        """
        測試：創建路線時勾選部分成員為已完成狀態應該成功
        
        測試步驟：
        1. 創建路線，勾選成員1和成員2為已完成
        2. 驗證創建成功
        3. 驗證成員1和成員2的完成狀態為True
        4. 驗證成員3的完成狀態為False
        """
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        response = self._create_route_with_member_completions(
            '部分完成路線',
            'V5',
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_formdata_and_checked_members(self):
        """
        測試：使用FormData格式創建路線時勾選成員應該成功
        
        測試步驟：
        1. 使用FormData格式創建路線，勾選成員為已完成
        2. 驗證創建成功
        3. 驗證成員的完成狀態正確
        """
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        data = {
            'name': 'FormData格式路線',
            'grade': 'V3',
            'member_completions': json.dumps(member_completions)
        }
        
        response = self.client.post(
            url,
            data=data,
            format='multipart'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"使用FormData創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_integer_member_ids(self):
        """
        測試：使用整數格式的成員ID創建路線時勾選成員應該成功
        
        測試步驟：
        1. 使用整數格式的成員ID創建路線，勾選成員為已完成
        2. 驗證創建成功
        3. 驗證成員的完成狀態正確
        """
        member_completions = {
            self.m1.id: True,  # 使用整數而不是字符串
            self.m2.id: True,
            self.m3.id: False
        }
        
        response = self._create_route_with_member_completions(
            '整數ID路線',
            'V4',
            member_completions
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"使用整數ID創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")
    
    def test_create_route_with_list_member_completions(self):
        """
        測試：當FormData將member_completions解析為列表時應該成功
        
        測試步驟：
        1. 模擬FormData將member_completions解析為列表的情況
        2. 驗證創建成功
        3. 驗證成員的完成狀態正確
        
        這個測試模擬了Django QueryDict可能將FormData中的值解析為列表的情況
        """
        url = f'/api/rooms/{self.room.id}/routes/'
        
        member_completions = {
            str(self.m1.id): True,
            str(self.m2.id): True,
            str(self.m3.id): False
        }
        
        # 模擬FormData將member_completions解析為列表的情況
        from django.http import QueryDict
        data = QueryDict(mutable=True)
        data['name'] = '列表格式路線'
        data['grade'] = 'V3'
        data.setlist('member_completions', [json.dumps(member_completions)])  # 設置為列表
        
        response = self.client.post(
            url,
            data=data,
            format='multipart'
        )
        
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            f"使用列表格式的member_completions創建路線應該成功，但返回了 {response.status_code}。錯誤: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        # 驗證路線已創建
        route = Route.objects.get(id=response.data['id'])
        self.assertIsNotNone(route)
        
        # 驗證成員完成狀態
        score1 = Score.objects.get(member=self.m1, route=route)
        self.assertTrue(score1.is_completed, "成員1應該標記為已完成")
        
        score2 = Score.objects.get(member=self.m2, route=route)
        self.assertTrue(score2.is_completed, "成員2應該標記為已完成")
        
        score3 = Score.objects.get(member=self.m3, route=route)
        self.assertFalse(score3.is_completed, "成員3應該標記為未完成")

