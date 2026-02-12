from django.db import models
from django.conf import settings

# 1. 映画館テーブル
class Theater(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="店舗名")
    address = models.CharField(max_length=200, verbose_name="住所")
    total_screens = models.IntegerField(default=0, verbose_name="所有スクリーン数")
    
    opening_time = models.TimeField(default="09:00", verbose_name="営業開始時間")
    last_start_time = models.TimeField(default="21:40", verbose_name="最終上映開始時間")

    def __str__(self):
        return self.name

# 2. シアター（スクリーン）テーブル
class Screen(models.Model):
    theater = models.ForeignKey(
        Theater, 
        on_delete=models.CASCADE, 
        related_name='screens', 
        verbose_name="映画館"
    )
    screen_number = models.IntegerField(verbose_name="シアター番号")
    capacity = models.IntegerField(verbose_name="座席数")
    screen_rank = models.IntegerField(default=2, verbose_name="ランク(1:大 / 2:中 / 3:小)")
    screen_size = models.CharField(max_length=50, default="Medium", verbose_name="サイズ名")

    def save(self, *args, **kwargs):
        # まず自分の映画館の最大席数を探す
        from django.db.models import Max
        max_cap = Screen.objects.filter(theater=self.theater).aggregate(Max('capacity'))['capacity__max']
        
        # 初めて登録する時など、max_capが無い場合は自分の席数を最大にする
        if not max_cap:
            max_cap = self.capacity

        # 割合を計算（プログラムがやってくれるので安心！）
        ratio = (self.capacity / max_cap) * 100

        if ratio >= 80:
            self.screen_rank = 1
            self.screen_size = "Large"
        elif ratio >= 50:
            self.screen_rank = 2
            self.screen_size = "Medium"
        else:
            self.screen_rank = 3
            self.screen_size = "Small"
        
        super().save(*args, **kwargs)

    class Meta:
        unique_together = (('theater', 'screen_number'),)

    def __str__(self):
        return f"{self.theater.name} - シアター{self.screen_number} ({self.screen_size})"

    class Meta:
        unique_together = (('theater', 'screen_number'),)

    def __str__(self):
        return f"{self.theater.name} - シアター{self.screen_number}"
    
class TheaterManager(models.Model):
    # これで「1つの映画館」に「何人もの支配人」を登録できます
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        verbose_name="支配人ユーザー"
    )
    theater = models.ForeignKey(
        Theater, 
        on_delete=models.CASCADE,
        verbose_name="担当する映画館"
    )

    class Meta:
        verbose_name = "映画館担当割当"
        # 同じ人が同じ館を二重に担当しないようにする設定
        unique_together = (('user', 'theater'),)

    def __str__(self):
        return f"{self.user.username} - {self.theater.name}"
    

class TheaterAssignment(models.Model): # この名前と views.py の名前が一致している必要があります
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="支配人")
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, verbose_name="映画館")

    class Meta:
        verbose_name = "担当映画館の割当"
        unique_together = (('user', 'theater'),)

class ScheduleTemplate(models.Model):
    # どの劇場用のひな形か（特定の劇場に縛る場合）
    theater = models.ForeignKey('Theater', on_delete=models.CASCADE, verbose_name="対象映画館")
    
    name = models.CharField(max_length=100, verbose_name="テンプレート名（例：超大作5回型）")
    
    # 開始時間をカンマ区切りで保存（例: "09:00, 12:30, 16:00, 19:30"）
    # 算数が苦手でも、ここを見れば「何時に始まるか」一目でわかります。
    start_times = models.CharField(max_length=255, verbose_name="開始時間リスト")
    
    # そのひな形が「朝向き」か「ゴールデン向き」かなどのメモ
    description = models.TextField(blank=True, verbose_name="説明・用途")

    def __str__(self):
        return f"{self.theater.name} - {self.name}"