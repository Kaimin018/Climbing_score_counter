"""
用戶認證相關序列化器
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.html import escape


class UserRegistrationSerializer(serializers.Serializer):
    """
    用戶註冊序列化器
    """
    username = serializers.CharField(
        max_length=150,
        min_length=3,
        help_text='用戶名（3-150個字符）'
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text='密碼（至少8個字符）'
    )
    password_confirm = serializers.CharField(
        write_only=True,
        help_text='確認密碼'
    )
    
    def validate_username(self, value):
        """驗證用戶名"""
        # 清理用戶輸入，防止 XSS
        username = escape(value)
        
        # 檢查用戶名格式
        if not username.replace('_', '').replace('.', '').isalnum():
            raise serializers.ValidationError('用戶名只能包含字母、數字、下劃線和點')
        
        return username
    
    def validate_email(self, value):
        """驗證郵箱"""
        if value:
            return escape(value)
        return value
    
    def validate_password(self, value):
        """驗證密碼強度"""
        validate_password(value)
        return value
    
    def validate(self, attrs):
        """驗證密碼確認"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '兩次輸入的密碼不一致'})
        return attrs


class UserLoginSerializer(serializers.Serializer):
    """
    用戶登錄序列化器
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate_username(self, value):
        """清理用戶輸入"""
        return escape(value)

