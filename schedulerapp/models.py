from django.db import models
from movies.models import Movie
from theaters.models import Screen

# 上映枠の「設計図」
class ScheduleTemplate(models.Model):
    name = models.CharField(max_length=50, verbose_name="テンプレート名")

    limit_runtime = models.IntegerField(
        default=120, 
        verbose_name="対応可能な最大映画時間(分)",
        help_text="この分数以下の映画にこのテンプレートが適用されます"
    )

    # 例: "09:00,11:20,13:40,16:00,18:20,20:40" (カンマ区切りで保存)
    start_times = models.CharField(
        max_length=255, 
        verbose_name="開始時間リスト", 
        help_text="カンマ区切りで入力してください"
    )
    # 例: "120,120,120,120,120,120"
    pattern_durations = models.CharField(
        max_length=255, 
        verbose_name="想定映画時間リスト", 
        help_text="各枠の映画の長さをカンマ区切りで入力"
    )

    class Meta:
        verbose_name = "スケジュールテンプレート"
        verbose_name_plural = "スケジュールテンプレート一覧"

    def __str__(self):
        return self.name

# 既存のスケジュール
class Schedule(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, verbose_name="映画")
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE, verbose_name="スクリーン")
    start_time = models.DateTimeField(verbose_name="上映開始日時")
    end_time = models.DateTimeField(verbose_name="上映終了日時")

    class Meta:
        verbose_name = "スケジュール"
        verbose_name_plural = "スケジュール一覧"

    def __str__(self):
        time_str = self.start_time.strftime('%Y/%m/%d %H:%M')
        return f"{self.screen}：{self.movie}（{time_str}〜）"