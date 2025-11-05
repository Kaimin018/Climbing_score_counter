# -*- coding: utf-8 -*-
import sys
import io
from django.core.management.base import BaseCommand
from scoring.models import Room, Member

# 設置輸出編碼為 UTF-8（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


class Command(BaseCommand):
    help = 'Initialize default data (create default room and members)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if data already exists',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        # 檢查是否已有房間
        existing_rooms = Room.objects.all()
        if existing_rooms.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Found {existing_rooms.count()} existing room(s). Use --force to recreate.'
                )
            )
            for room in existing_rooms:
                self.stdout.write(f'  - {room.name} (ID: {room.id})')
            return

        # 創建默認房間
        if force:
            Room.objects.filter(name="竹北岩館挑戰賽").delete()
            self.stdout.write(self.style.WARNING('Deleted existing room: 竹北岩館挑戰賽'))

        room, created = Room.objects.get_or_create(
            name="竹北岩館挑戰賽",
            defaults={'standard_line_score': 12}
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Created room: {room.name} (ID: {room.id})')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'[OK] Using existing room: {room.name} (ID: {room.id})')
            )

        # 檢查是否已有成員
        existing_members = room.members.all()
        if existing_members.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Room has {existing_members.count()} existing member(s). Use --force to recreate.'
                )
            )
            return

        # 刪除現有成員（如果強制創建）
        if force and existing_members.exists():
            count = existing_members.count()
            existing_members.delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {count} existing member(s)')
            )

        # 創建成員（常態組）
        member1, created1 = Member.objects.get_or_create(
            room=room,
            name="王小明",
            defaults={'is_custom_calc': False}
        )
        if created1:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created member (Normal): {member1.name}'))

        member2, created2 = Member.objects.get_or_create(
            room=room,
            name="李大華",
            defaults={'is_custom_calc': False}
        )
        if created2:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created member (Normal): {member2.name}'))

        # 創建成員（客製化組）
        member3, created3 = Member.objects.get_or_create(
            room=room,
            name="張三",
            defaults={'is_custom_calc': True}
        )
        if created3:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created member (Custom): {member3.name}'))

        self.stdout.write(
            self.style.SUCCESS(
                f'\nInitialization complete!\n'
                f'   Room Name: {room.name}\n'
                f'   Room ID: {room.id}\n'
                f'   Standard Line Score (L): {room.standard_line_score}\n'
                f'   Member Count: {room.members.count()}\n'
                f'\nVisit leaderboard: http://127.0.0.1:8000/api/leaderboard/{room.id}/'
            )
        )

