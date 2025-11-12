#!/usr/bin/env python
"""
快速測試生產環境權限
"""
import os
import sys
import django

# 設置環境變數（在導入 Django 之前）
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climbing_system.settings')
os.environ['DEBUG'] = 'False'

django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from scoring.permissions import IsMemberOrReadOnly

print("=" * 60)
print("Production Permission Test")
print("=" * 60)
print(f"DEBUG: {settings.DEBUG}")
print(f"Permission Classes: {settings.REST_FRAMEWORK.get('DEFAULT_PERMISSION_CLASSES', [])}")
print()

# Clean up existing test users
User.objects.filter(username__in=['guest_test_prod', 'regular_test_prod']).delete()

# Create test users
guest = User.objects.create_user(username='guest_test_prod', password='dummy')
regular = User.objects.create_user(username='regular_test_prod', password='dummy')

# 測試權限
factory = APIRequestFactory()
permission = IsMemberOrReadOnly()

# Test guest POST (should fail)
# Use force_authenticate to properly set authentication
from rest_framework.test import force_authenticate
request = factory.post('/api/rooms/', {'name': 'test'})
force_authenticate(request, user=guest)
drf_request = Request(request)
print(f"Guest user authenticated: {drf_request.user.is_authenticated}")
print(f"Guest username: {drf_request.user.username}")
print(f"Is guest: {drf_request.user.username.startswith('guest_')}")
guest_post_permission = permission.has_permission(drf_request, None)
print(f"Guest POST permission: {guest_post_permission} (should be False)")
print()

# Test regular user POST (should succeed)
request = factory.post('/api/rooms/', {'name': 'test'})
force_authenticate(request, user=regular)
drf_request = Request(request)
print(f"Regular user authenticated: {drf_request.user.is_authenticated}")
print(f"Regular username: {drf_request.user.username}")
print(f"Is guest: {drf_request.user.username.startswith('guest_')}")
regular_post_permission = permission.has_permission(drf_request, None)
print(f"Regular user POST permission: {regular_post_permission} (should be True)")
print()

# Test guest GET (should succeed)
request = factory.get('/api/rooms/')
request.user = guest
guest_get_permission = permission.has_permission(Request(request), None)
print(f"Guest GET permission: {guest_get_permission} (should be True)")

print()
print("=" * 60)
print("Test Results")
print("=" * 60)
if not guest_post_permission and regular_post_permission and guest_get_permission:
    print("SUCCESS: All tests passed!")
    sys.exit(0)
else:
    print("FAILED: Test failed")
    print(f"   Guest POST: {guest_post_permission} (expected: False)")
    print(f"   Regular user POST: {regular_post_permission} (expected: True)")
    print(f"   Guest GET: {guest_get_permission} (expected: True)")
    sys.exit(1)

