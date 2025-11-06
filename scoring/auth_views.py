"""
用戶認證相關視圖
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.utils.html import escape
from .auth_serializers import UserRegistrationSerializer, UserLoginSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    用戶註冊
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        # 清理用戶輸入，防止 XSS
        username = escape(serializer.validated_data['username'])
        email = escape(serializer.validated_data.get('email', ''))
        password = serializer.validated_data['password']
        
        # 檢查用戶名是否已存在
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': '用戶名已存在'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 創建用戶
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # 自動登錄
        login(request, user)
        
        # 確保 session 已保存
        request.session.save()
        
        return Response({
            'message': '註冊成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    用戶登錄
    """
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        # 清理用戶輸入
        username = escape(serializer.validated_data['username'])
        password = serializer.validated_data['password']
        
        # 驗證用戶
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            
            # 確保 session 已保存
            request.session.save()
            
            return Response({
                'message': '登錄成功',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': '用戶名或密碼錯誤'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    用戶登出
    """
    logout(request)
    return Response({'message': '登出成功'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_user_view(request):
    """
    獲取當前登錄用戶信息
    """
    return Response({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'is_authenticated': request.user.is_authenticated
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def guest_login_view(request):
    """
    訪客登錄
    創建或獲取訪客用戶，並自動登錄
    目前訪客用戶與普通用戶權限相同，後續可調整
    """
    from django.utils import timezone
    import random
    import string
    
    # 生成唯一的訪客用戶名（使用時間戳和隨機字符串）
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    guest_username = f'guest_{timestamp}_{random_str}'
    
    # 檢查是否已存在訪客用戶（如果已登錄且是訪客，直接返回）
    if request.user.is_authenticated and request.user.username.startswith('guest_'):
        return Response({
            'message': '訪客登錄成功',
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'is_guest': True
            }
        }, status=status.HTTP_200_OK)
    
    # 創建訪客用戶（使用隨機密碼，因為訪客不需要密碼登錄）
    random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    guest_user = User.objects.create_user(
        username=guest_username,
        email='',
        password=random_password,
        is_active=True
    )
    
    # 自動登錄
    login(request, guest_user)
    
    # 確保 session 已保存
    request.session.save()
    
    return Response({
        'message': '訪客登錄成功',
        'user': {
            'id': guest_user.id,
            'username': guest_user.username,
            'email': guest_user.email,
            'is_guest': True
        },
        'session_key': request.session.session_key  # 用於調試
    }, status=status.HTTP_200_OK)