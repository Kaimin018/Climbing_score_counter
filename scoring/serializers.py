from rest_framework import serializers
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
    member_completions = serializers.DictField(
        child=serializers.BooleanField(),
        write_only=True,
        help_text="格式: {'member_id': is_completed}"
    )
    grade = serializers.CharField(required=True, allow_blank=False, error_messages={
        'required': '難度等級為必填項目',
        'blank': '難度等級不能為空'
    })

    class Meta:
        model = Route
        fields = ['name', 'grade', 'photo', 'photo_url', 'member_completions']

    def create(self, validated_data):
        member_completions = validated_data.pop('member_completions', {})
        room = self.context['room']
        
        # 處理 member_completions（可能是 JSON 字符串）
        if isinstance(member_completions, str):
            import json
            try:
                member_completions = json.loads(member_completions)
            except json.JSONDecodeError:
                member_completions = {}
        
        # 創建路線
        route = Route.objects.create(room=room, **validated_data)
        
        # 批量創建所有成員的 Score 記錄
        members = room.members.all()
        for member in members:
            is_completed = member_completions.get(str(member.id), False)
            Score.objects.create(
                member=member,
                route=route,
                is_completed=is_completed
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
    
    def validate_member_completions(self, value):
        """驗證 member_completions 字段"""
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        # 如果值為 None 或空字符串，返回 None
        if value is None or (isinstance(value, str) and value.strip() == ''):
            logger.info(f"[RouteUpdateSerializer.validate] member_completions 為空，返回 None")
            return None
        
        logger.info(f"[RouteUpdateSerializer.validate] member_completions 類型: {type(value)}, 值: {value}")
        
        # 如果值是字符串，嘗試解析 JSON
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                logger.info(f"[RouteUpdateSerializer.validate] JSON 字符串解析成功: {parsed}")
                # 確保解析後是字典
                if not isinstance(parsed, dict):
                    logger.warning(f"[RouteUpdateSerializer.validate] 解析結果不是字典，轉換為空字典")
                    return {}
                return parsed
            except json.JSONDecodeError as e:
                logger.error(f"[RouteUpdateSerializer.validate] JSON 解析失敗: {e}, 原始值: {value}")
                return {}
        
        # 如果已經是字典，直接返回
        if isinstance(value, dict):
            logger.info(f"[RouteUpdateSerializer.validate] member_completions 已經是字典: {value}")
            return value
        
        logger.warning(f"[RouteUpdateSerializer.validate] member_completions 類型不正確: {type(value)}, 返回空字典")
        return {}

    def update(self, instance, validated_data):
        import logging
        logger = logging.getLogger(__name__)
        
        member_completions = validated_data.pop('member_completions', None)
        room = instance.room
        
        logger.info(f"[RouteUpdateSerializer] 開始更新路線 ID={instance.id}, name={instance.name}")
        logger.info(f"[RouteUpdateSerializer] 接收到的 member_completions 類型: {type(member_completions)}, 值: {member_completions}")
        
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
            logger.info(f"[RouteUpdateSerializer] member_completions 不為 None，開始處理")
            # 處理 member_completions（可能是 JSON 字符串）
            if isinstance(member_completions, str):
                logger.info(f"[RouteUpdateSerializer] member_completions 是字符串，嘗試解析 JSON: {member_completions}")
                import json
                try:
                    member_completions = json.loads(member_completions)
                    logger.info(f"[RouteUpdateSerializer] JSON 解析成功: {member_completions}")
                except json.JSONDecodeError as e:
                    logger.error(f"[RouteUpdateSerializer] JSON 解析失敗: {e}")
                    member_completions = {}
            
            # 確保 member_completions 是字典類型
            if not isinstance(member_completions, dict):
                logger.warning(f"[RouteUpdateSerializer] member_completions 不是字典類型，轉換為空字典。原始類型: {type(member_completions)}")
                member_completions = {}
            
            logger.info(f"[RouteUpdateSerializer] 處理後的 member_completions: {member_completions}, 類型: {type(member_completions)}")
            
            # 獲取所有成員的成績記錄
            all_members = list(room.members.all())
            logger.info(f"[RouteUpdateSerializer] 房間共有 {len(all_members)} 個成員: {[m.id for m in all_members]}")
            
            for member in all_members:
                score, created = Score.objects.get_or_create(
                    member=member,
                    route=instance,
                    defaults={'is_completed': False}
                )
                # 更新完成狀態：如果成員在字典中，使用提供的值；否則設為 False（未勾選）
                # 確保 member_id 作為字符串進行比較
                member_id_str = str(member.id)
                member_id_int = member.id
                logger.debug(f"[RouteUpdateSerializer] 處理成員 ID={member.id} (字符串: {member_id_str}), 名稱: {member.name}")
                
                # 嘗試多種 key 格式
                is_completed = None
                if member_id_str in member_completions:
                    is_completed = member_completions[member_id_str]
                    logger.debug(f"[RouteUpdateSerializer] 使用字符串 key '{member_id_str}' 找到值: {is_completed}")
                elif member_id_int in member_completions:
                    is_completed = member_completions[member_id_int]
                    logger.debug(f"[RouteUpdateSerializer] 使用整數 key '{member_id_int}' 找到值: {is_completed}")
                else:
                    is_completed = False
                    logger.debug(f"[RouteUpdateSerializer] 成員 ID {member.id} 不在 member_completions 中，設為 False")
                
                # 確保 is_completed 是布林值
                if isinstance(is_completed, str):
                    is_completed = is_completed.lower() in ('true', '1', 'yes')
                    logger.debug(f"[RouteUpdateSerializer] 將字符串 '{is_completed}' 轉換為布林值: {is_completed}")
                
                old_status = score.is_completed
                score.is_completed = bool(is_completed)
                score.save()
                logger.info(f"[RouteUpdateSerializer] 成員 {member.name} (ID={member.id}): {old_status} -> {score.is_completed}")
        else:
            logger.info(f"[RouteUpdateSerializer] member_completions 為 None，跳過更新完成狀態")
        
        # 觸發計分更新
        from .models import update_scores
        update_scores(room.id)
        logger.info(f"[RouteUpdateSerializer] 路線更新完成，已觸發計分更新")
        
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
    
    def to_representation(self, instance):
        """確保嵌套的 RouteSerializer 能正確獲取 context"""
        representation = super().to_representation(instance)
        # 手動序列化 routes 以確保 context 正確傳遞
        request = self.context.get('request')
        representation['routes'] = RouteSerializer(
            instance.routes.all(), 
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
