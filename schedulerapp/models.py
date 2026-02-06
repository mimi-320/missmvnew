from django.db import models
from movies.models import Movie
from theaters.models import Screen

class Schedule(models.Model):
    
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name="映画")
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, verbose_name="スクリーン")
    
    # AIが計算した結果をここに保存する
    start_time = models.DateTimeField(verbose_name="上映開始日時")
    end_time = models.DateTimeField(verbose_name="上映終了日時")

    class Meta:
        verbose_name = "スケジュール"
        verbose_name_plural = "スケジュール一覧"

    def __str__(self):
        return f"{self.screen}：{self.movie}（{self.start_time}〜）"