from django.db import models
import datetime
import math

class Movie(models.Model):
    # --- 基本情報 ---
    title = models.CharField(max_length=200, verbose_name="タイトル")
    runtime = models.IntegerField(verbose_name="上映時間(分)")
    release_date = models.DateField(verbose_name="公開日")
    budget = models.BigIntegerField(default=0, verbose_name="予算")
    company = models.CharField(max_length=100, verbose_name="制作会社")
    language = models.CharField(max_length=10, verbose_name="言語") 

    # --- 監督・俳優（名前だけ） ---
    director_name = models.CharField(max_length=100, verbose_name="監督名")
    cast1_name = models.CharField(max_length=100, verbose_name="俳優1")
    cast2_name = models.CharField(max_length=100, verbose_name="俳優2")
    cast3_name = models.CharField(max_length=100, verbose_name="俳優3")

    # --- 基本フラグ ---
    is_series = models.BooleanField(default=False, verbose_name="シリーズものか")
    is_adventure = models.BooleanField(default=False, verbose_name="アドベンチャー")
    is_fantasy = models.BooleanField(default=False, verbose_name="ファンタジー")
    is_animation = models.BooleanField(default=False, verbose_name="アニメーション")
    is_action = models.BooleanField(default=False, verbose_name="アクション")
    is_drama = models.BooleanField(default=False, verbose_name="ドラマ")

    def __str__(self):
        return self.title
    
class NowShowingMovie(models.Model):
    theater = models.ForeignKey(
        'theaters.Theater', 
        on_delete=models.CASCADE, 
        verbose_name="映画館",
        null=True, blank=True # 既存データがある場合はこれをつけておくと安全
    )

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE,related_name='now_showings')

    # --- 【追加】ランキング計算に使うためのカラム ---
    predicted_final_revenue = models.BigIntegerField(default=0, verbose_name="予想最終興行収入")
    current_revenue = models.BigIntegerField(default=0, verbose_name="現在までの累計売上")
    priority_rank = models.IntegerField(default=999, verbose_name="計算後優先順位")
    current_week_num = models.IntegerField(default=1, verbose_name="現在の公開週数")
    is_ending_soon = models.BooleanField(default=1, verbose_name="公開終了フェーズ") # ボタンで切り替え


    # --- 契約条件 (ここはそのまま) ---
    contract_weeks = models.IntegerField(default=1)
    min_daily_runs = models.IntegerField(default=1)
    required_time_slot = models.CharField(max_length=100, blank=True, null=True)

    release_month = models.IntegerField(default=1)
    release_year = models.IntegerField(default=2026)
    
    is_lang_ja = models.IntegerField(default=0)
    is_lang_en = models.IntegerField(default=0)

    company_rank = models.IntegerField(default=0)
    director_rank = models.FloatField(default=0.0)
    cast_rank = models.FloatField(default=0.0)
    cast_total_score = models.FloatField(default=0.0)

    is_scifi = models.IntegerField(default=0)
    is_family = models.IntegerField(default=0)
    is_comedy = models.IntegerField(default=0)
    is_romance = models.IntegerField(default=0)
    is_horror = models.IntegerField(default=0)
    is_thriller = models.IntegerField(default=0)

    rival_count_is_adventure = models.IntegerField(default=0)
    rival_count_is_fantasy = models.IntegerField(default=0)
    rival_count_is_animation = models.IntegerField(default=0)
    rival_count_is_family = models.IntegerField(default=0)
    rival_count_is_drama = models.IntegerField(default=0)
    rival_count_is_action = models.IntegerField(default=0)

    budget_cast_score = models.FloatField(default=0.0, verbose_name="budget*cast")
    budget_relative_score = models.FloatField(default=0.0)
    cast_relative_score = models.FloatField(default=0.0)

    prediction_score = models.FloatField(default=0.0, verbose_name="AI期待度スコア")

    def __str__(self):
        return f"【上映中】{self.movie.title}"
    
class DistributionContract(models.Model):
    movie = models.OneToOneField('NowShowingMovie', on_delete=models.CASCADE, verbose_name="対象映画")
    
    # --- 既存の項目 ---
    required_screen_rank = models.IntegerField(
        null=True, blank=True, 
        verbose_name="必須スクリーンランク(1:大 / 2:中 / 3:小)"
    )
    required_daily_runs = models.IntegerField(
        null=True, blank=True, 
        verbose_name="1日の最低上映回数"
    )
    contract_period_weeks = models.IntegerField(
        null=True, blank=True, 
        verbose_name="契約維持週数"
    )

    # ---上映形態の指定 ---
    SCREENING_TYPE_CHOICES = [
        ('exclusive', 'シアター独占'),
        ('share', '他作品とシェア'),
        ('flexible', '指定なし（ランキング順）'),
    ]
    screening_type = models.CharField(
        max_length=20,
        choices=SCREENING_TYPE_CHOICES,
        default='flexible',
        verbose_name="上映形態"
    )
    
    special_notes = models.TextField(blank=True, verbose_name="時間指定などの特記事項")

    def __str__(self):
        return f"{self.movie.movie.title} の契約条件"