from django.db import models
from django.conf import settings

# 1. 映画館テーブル
class Theater(models.Model):
    # 💡 ここから manager 項目を削除しました！
    name = models.CharField(max_length=100, unique=True, verbose_name="店舗名")
    address = models.CharField(max_length=200, verbose_name="住所")
    total_screens = models.IntegerField(default=0, verbose_name="所有スクリーン数")

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
    screen_size = models.CharField(max_length=50, verbose_name="スクリーンサイズ")

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