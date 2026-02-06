from django.db import models

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
    movie = models.OneToOneField(Movie, on_delete=models.CASCADE, verbose_name="対象映画")

    # --- 契約条件 ---
    contract_weeks = models.IntegerField(default=1)
    min_daily_runs = models.IntegerField(default=1)
    required_time_slot = models.CharField(max_length=100, blank=True, null=True)

    # --- AIの入力に使う算出用カラム (追加分) ---
    release_month = models.IntegerField(default=1) # 1~12月
    release_year = models.IntegerField(default=2026)
    
    # 言語(0か1で保存)
    is_lang_ja = models.IntegerField(default=0)
    is_lang_en = models.IntegerField(default=0)

    # ランク系
    company_rank = models.IntegerField(default=0)
    director_rank = models.FloatField(default=0.0)
    cast_rank = models.FloatField(default=0.0)
    cast_total_score = models.FloatField(default=0.0)

    # ジャンル詳細
    is_scifi = models.IntegerField(default=0)
    is_family = models.IntegerField(default=0)
    is_comedy = models.IntegerField(default=0)
    is_romance = models.IntegerField(default=0)
    is_horror = models.IntegerField(default=0)
    is_thriller = models.IntegerField(default=0)

    # ライバル数
    rival_count_is_adventure = models.IntegerField(default=0)
    rival_count_is_fantasy = models.IntegerField(default=0)
    rival_count_is_animation = models.IntegerField(default=0)
    rival_count_is_family = models.IntegerField(default=0)
    rival_count_is_drama = models.IntegerField(default=0)
    rival_count_is_action = models.IntegerField(default=0)

    # 相対・掛け合わせ
    budget_cast_score = models.FloatField(default=0.0, verbose_name="budget*cast")
    budget_relative_score = models.FloatField(default=0.0)
    cast_relative_score = models.FloatField(default=0.0)

    # AIが出した最終的な答え
    prediction_score = models.FloatField(default=0.0, verbose_name="AI期待度スコア")

    def __str__(self):
        return f"【上映中】{self.movie.title}"