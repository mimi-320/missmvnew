from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, ManagerProfile

# 1. まず「どう表示するか」というルール（クラス）を先に書く
class CustomUserAdmin(UserAdmin):
    # 編集画面に項目を追加
    fieldsets = UserAdmin.fieldsets + (
        ('追加権限', {'fields': ('is_top_admin', 'is_manager')}),
    )
    # 一覧画面に表示する列
    list_display = ['username', 'email', 'is_top_admin', 'is_manager', 'is_staff']

# 2. 【重要】「Userモデル」を「CustomUserAdminのルール」で登録する
# admin.site.register(User, UserAdmin) ← これを消して、下のように書く！
admin.site.register(User, CustomUserAdmin)

# 3. その他はそのまま
admin.site.register(ManagerProfile)