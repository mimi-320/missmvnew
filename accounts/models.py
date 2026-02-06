from django.db import models
from django.contrib.auth.models import AbstractUser,Group, Permission

# 1. カスタムユーザーモデル
class User(AbstractUser):
    # 管理人か支配人かを判別するフラグ
    is_top_admin = models.BooleanField(default=False, verbose_name="管理人フラグ")
    is_manager = models.BooleanField(default=False, verbose_name="支配人フラグ")

    # --- ここから追加：ケンカを止めるための設定 ---
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",  # 名前を変えて重複を避ける
        blank=True,
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_set",  # 名前を変えて重複を避ける
        blank=True,
        verbose_name='user permissions',
    )

# 2. 支配人プロフィールテーブル（支配人専用の追加情報）
class ManagerProfile(models.Model):
    # Userモデルと1対1で紐付け
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='manager_profile')
    
    # 担当映画館（theatersアプリのTheaterモデルを参照）
    theater = models.ForeignKey('theaters.Theater', on_delete=models.SET_NULL, null=True, verbose_name="担当映画館")
    
    # 在籍フラグ
    is_active_staff = models.BooleanField(default=True, verbose_name="在籍中")
    
    # 初回パスワード変更フラグ
    needs_password_change = models.BooleanField(default=True, verbose_name="初回パスワード変更が必要")
    
    # 電話番号
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="電話番号")

    def __str__(self):
        return f"{self.user.username} (支配人)"