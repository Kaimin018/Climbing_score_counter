from rest_framework import serializers
from django.utils.html import escape
from .models import Room, Member, Route, Score


class ScoreSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.name', read_only=True)
    member_id = serializers.IntegerField(source='member.id', read_only=True)

    class Meta:
        model = Score
        fields = ['id', 'member_id', 'member_name', 'is_completed', 'score_attained']


class RouteSerializer(serializers.ModelSerializer):
    scores = ScoreSerializer(many=True, read_only=True)
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = ['id', 'name', 'grade', 'photo', 'photo_url', 'scores', 'created_at']
    
    def to_representation(self, instance):
        """確保 scores 數據是最新的"""
        representation = super().to_representation(instance)
        
        # 從數據庫重新獲取 scores 以確保數據最新（避免緩存問題）
        # 如果已經預取，直接使用；否則重新查詢
        if hasattr(instance, '_prefetched_objects_cache') and 'scores' in instance._prefetched_objects_cache:
            scores = instance._prefetched_objects_cache['scores']
        else:
            scores = instance.scores.all()
        
        representation['scores'] = ScoreSerializer(scores, many=True).data
        return representation
    
    def get_photo_url(self, obj):
        """返回照片的完整 URL"""
        if obj.photo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.photo.url)
            return obj.photo.url
        # 如果沒有上傳照片，返回舊的 photo_url（向後兼容）
        return obj.photo_url if obj.photo_url else ''


class RouteCreateSerializer(serializers.ModelSerializer):
    """用於創建路線並批量創建成績記錄"""
    member_completions = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="格式: JSON 字符串，如 '{\"member_id\": true}'"
    )
    grade = serializers.CharField(required=True, allow_blank=False, error_messages={
        'required': '難度等級為必填項目',
        'blank': '難度等級不能為空'
    })

    class Meta:
        model = Route
        fields = ['name', 'grade', 'photo', 'photo_url', 'member_completions']

    def validate_name(self, value):
        """驗證並清理路線名稱，防止 XSS"""
        if value:
            return escape(value.strip())
        return value
    
    def validate_grade(self, value):
        """驗證並清理難度等級，防止 XSS"""
        if value:
            return escape(value.strip())
        return value
    
    def validate_member_completions(self, value):
        """驗證並解析 member_completions，防止 SQL 注入"""
        import json
        
        # 如果值為 None 或空字符串，返回空字典
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return {}
        
        # 如果值是字符串，嘗試解析 JSON
        if isinstance(value, str):
            # 限制 JSON 字符串長度，防止過大的輸入
            if len(value) > 10000:
                raise serializers.ValidationError('member_completions 數據過大')
            try:
                parsed = json.loads(value)
                # 確保解析後是字典
                if not isinstance(parsed, dict):
                    raise serializers.ValidationError('member_completions 必須是 JSON 對象')
                # 驗證字典中的值都是布林值或可轉換為布林值
                for key, val in parsed.items():
                    if not isinstance(key, (str, int)):
                        raise serializers.ValidationError('member_completions 的鍵必須是字符串或整數')
                    if not isinstance(val, bool):
                        # 嘗試轉換為布林值
                        if isinstance(val, str):
                            parsed[key] = val.lower() in ('true', '1', 'yes')
                        else:
                            parsed[key] = bool(val)
                return parsed
            except json.JSONDecodeError:
                raise serializers.ValidationError('member_completions 必須是有效的 JSON 格式')
        
        # 如果已經是字典，直接返回
        return value if isinstance(value, dict) else {}
    
    def create(self, validated_data):
        member_completions = validated_data.pop('member_completions', {})
        room = self.context['room']
        
        # 創建路線
        route = Route.objects.create(room=room, **validated_data)
        
        # 批量創建所有成員的 Score 記錄
        members = room.members.all()
        for member in members:
            # 嘗試兩種 key 格式：字符串和整數
            member_id_str = str(member.id)
            member_id_int = member.id
            
            is_completed = False
            if member_id_str in member_completions:
                is_completed = member_completions[member_id_str]
            elif member_id_int in member_completions:
                is_completed = member_completions[member_id_int]
            
            # 確保 is_completed 是布林值
            if isinstance(is_completed, str):
                is_completed = is_completed.lower() in ('true', '1', 'yes')
            
            Score.objects.create(
                member=member,
                route=route,
                is_completed=bool(is_completed)
            )
        
        # 觸發計分更新
        from .models import update_scores
        update_scores(room.id)
        
        return route


class RouteUpdateSerializer(serializers.ModelSerializer):
    """用於更新路線並批量更新成績記錄"""
    member_completions = serializers.CharField(
        write_only=True,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="格式: JSON 字符串，如 '{\"member_id\": true}'"
    )

    class Meta:
        model = Route
        fields = ['name', 'grade', 'photo', 'photo_url', 'member_completions']
    
    def validate_name(self, value):
        """驗證並清理路線名稱，防止 XSS"""
        if value:
            return escape(value.strip())
        return value
    
    def validate_grade(self, value):
        """驗證並清理難度等級，防止 XSS"""
        if value:
            return escape(value.strip())
        return value
    
    def validate_member_completions(self, value):
        """驗證 member_completions 字段，防止 SQL 注入"""
        import json
        
        # 如果值為 None 或空字符串，返回 None
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None
        
        # 如果值是字符串，嘗試解析 JSON
        if isinstance(value, str):
            # 限制 JSON 字符串長度，防止過大的輸入
            if len(value) > 10000:
                raise serializers.ValidationError('member_completions 數據過大')
            try:
                parsed = json.loads(value)
                # 確保解析後是字典
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        
        # 如果已經是字典，直接返回
        return value if isinstance(value, dict) else {}

    def update(self, instance, validated_data):
        member_completions = validated_data.pop('member_completions', None)
        room = instance.room
        
        # 更新路線信息（只更新提供的字段）
        if 'name' in validated_data:
            instance.name = validated_data['name']
        if 'grade' in validated_data:
            instance.grade = validated_data['grade']
        # 如果提供了新照片，更新照片
        if 'photo' in validated_data:
            instance.photo = validated_data.get('photo')
        # 向後兼容：如果提供了 photo_url（舊版），保留它
        if 'photo_url' in validated_data:
            instance.photo_url = validated_data.get('photo_url', instance.photo_url)
        instance.save()
        
        # 如果提供了成員完成狀態，批量更新
        if member_completions is not None:
            # 處理 member_completions（可能是 JSON 字符串）
            if isinstance(member_completions, str):
                import json
                try:
                    member_completions = json.loads(member_completions)
                except json.JSONDecodeError:
                    member_completions = {}
            
            # 確保 member_completions 是字典類型
            if not isinstance(member_completions, dict):
                member_completions = {}
            
            # 更新所有成員的完成狀態
            for member in room.members.all():
                score, created = Score.objects.get_or_create(
                    member=member,
                    route=instance,
                    defaults={'is_completed': False}
                )
                # 嘗試多種 key 格式（字符串和整數）
                member_id_str = str(member.id)
                member_id_int = member.id
                
                is_completed = False
                if member_id_str in member_completions:
                    is_completed = member_completions[member_id_str]
                elif member_id_int in member_completions:
                    is_completed = member_completions[member_id_int]
                
                # 確保 is_completed 是布林值
                if isinstance(is_completed, str):
                    is_completed = is_completed.lower() in ('true', '1', 'yes')
                
                score.is_completed = bool(is_completed)
                score.save()
        
        # 觸發計分更新
        from .models import update_scores
        update_scores(room.id)
        
        return instance


class MemberSerializer(serializers.ModelSerializer):
    completed_routes_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Member
        fields = ['id', 'room', 'name', 'is_custom_calc', 'total_score', 'completed_routes_count']
        read_only_fields = ['total_score', 'completed_routes_count']

    def validate_room(self, value):
        """驗證房間是否存在"""
        if not value:
            raise serializers.ValidationError("房間 ID 不能為空")
        return value

    def validate(self, data):
        """驗證成員名稱在同一房間內是否重複"""
        room = data.get('room')
        name = data.get('name')
        
        # 如果是更新操作，獲取當前實例
        instance = self.instance
        
        if room and name:
            # 檢查同一房間內是否有相同名稱的成員
            existing_member = Member.objects.filter(room=room, name=name)
            
            # 如果是更新操作，排除當前成員
            if instance:
                existing_member = existing_member.exclude(id=instance.id)
            
            if existing_member.exists():
                raise serializers.ValidationError({
                    'name': f'該房間內已存在名為 "{name}" 的成員，請使用不同的名稱。'
                })
        
        return data

    def create(self, validated_data):
        """創建成員並為所有現有路線創建 Score 記錄"""
        member = Member.objects.create(**validated_data)
        
        # 為新成員創建所有現有路線的 Score 記錄（默認未完成）
        room = member.room
        routes = room.routes.all()
        for route in routes:
            Score.objects.create(
                member=member,
                route=route,
                is_completed=False
            )
        
        # 觸發計分更新（會自動更新standard_line_score）
        from .models import update_scores
        update_scores(room.id)
        
        return member

    def update(self, instance, validated_data):
        """更新成員資訊"""
        # 更新成員資訊
        instance.name = validated_data.get('name', instance.name)
        instance.is_custom_calc = validated_data.get('is_custom_calc', instance.is_custom_calc)
        instance.save()
        
        # 觸發計分更新（會自動更新standard_line_score）
        from .models import update_scores
        update_scores(instance.room.id)
        
        return instance


class RoomSerializer(serializers.ModelSerializer):
    members = MemberSerializer(many=True, read_only=True)
    routes = RouteSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'standard_line_score', 'members', 'routes', 'created_at']
    
    def validate_name(self, value):
        """驗證並清理房間名稱，防止 XSS"""
        if value:
            cleaned_name = escape(value.strip())
            # 限制名稱長度
            if len(cleaned_name) > 200:
                raise serializers.ValidationError('房間名稱不能超過200個字符')
            return cleaned_name
        return value
    
    def to_representation(self, instance):
        """確保嵌套的 RouteSerializer 能正確獲取 context"""
        representation = super().to_representation(instance)
        # 手動序列化 routes 以確保 context 正確傳遞
        request = self.context.get('request')
        
        # 強制重新查詢 routes 並預取 scores 關係，避免緩存問題
        # 使用 select_related 和 prefetch_related 確保數據完整
        # 如果 instance 已經有 prefetch_related，這會使用它；否則重新查詢
        if hasattr(instance, '_prefetched_objects_cache') and 'routes' in instance._prefetched_objects_cache:
            # 如果已經預取，使用預取的數據
            routes = instance._prefetched_objects_cache['routes']
        else:
            # 否則重新查詢並預取
            routes = instance.routes.prefetch_related('scores__member').all()
        
        representation['routes'] = RouteSerializer(
            routes, 
            many=True, 
            context={'request': request} if request else {}
        ).data
        return representation


class LeaderboardSerializer(serializers.Serializer):
    """排行榜序列化器"""
    room_info = serializers.DictField()
    leaderboard = MemberSerializer(many=True)


class ScoreUpdateSerializer(serializers.ModelSerializer):
    """用於更新成績狀態"""
    class Meta:
        model = Score
        fields = ['is_completed']
