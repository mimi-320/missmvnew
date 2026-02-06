# movies/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Movie, NowShowingMovie
from .apps import MoviesConfig

@receiver(post_save, sender=Movie)
def auto_fill_ai_data(sender, instance, **kwargs):
    # パックが読み込めていなければ何もしない
    if not MoviesConfig.ai_pack:
        return

    pack = MoviesConfig.ai_pack
    showing, _ = NowShowingMovie.objects.get_or_create(movie=instance)

    # 1. 名簿からランクを引く
    showing.director_rank = pack['rank_map'].get(instance.director_name, 0)
    showing.company_rank = pack['comp_map'].get(instance.company, 0)

    # 2. キャスト合計（算数はシステムにお任せ！）
    s1 = pack['actor_map'].get(instance.cast1_name, 0)
    s2 = pack['actor_map'].get(instance.cast2_name, 0)
    s3 = pack['actor_map'].get(instance.cast3_name, 0)
    showing.cast_total_score = s1 + s2 + s3

    # ... 他の項目も同様に ...

    showing.save()

@receiver(post_save, sender=Movie)
def auto_fill_ai_data(sender, instance, created, **kwargs):
    # パックが読み込めていなければ何もしない
    if not MoviesConfig.ai_pack:
        return

    pack = MoviesConfig.ai_pack
    
    # 上映設定用のデータ（箱）を準備
    showing, _ = NowShowingMovie.objects.get_or_create(movie=instance)

    # --- 1. 名簿(map)から値を引いて埋める ---
    showing.director_rank = pack['rank_map'].get(instance.director_name, 0)
    showing.company_rank = pack['comp_map'].get(instance.company, 0)

    # --- 2. キャスト合計スコア（3人分を足し算） ---
    s1 = pack['actor_map'].get(instance.cast1_name, 0)
    s2 = pack['actor_map'].get(instance.cast2_name, 0)
    s3 = pack['actor_map'].get(instance.cast3_name, 0)
    showing.cast_total_score = s1 + s2 + s3

    # --- 3. 日付から年・月を分解 ---
    if instance.release_date:
        showing.release_year = instance.release_date.year
        showing.release_month = instance.release_date.month

    # --- 4. 言語を 0 か 1 に変換 (AI用) ---
    showing.is_lang_ja = 1 if instance.language == 'ja' else 0
    showing.is_lang_en = 1 if instance.language == 'en' else 0

    # --- 5. ジャンルフラグのコピー (True/False を 1/0 に) ---
    showing.is_series = 1 if instance.is_series else 0
    showing.is_animation = 1 if instance.is_animation else 0
    showing.is_action = 1 if instance.is_action else 0
    showing.is_adventure = 1 if instance.is_adventure else 0
    showing.is_fantasy = 1 if instance.is_fantasy else 0
    showing.is_drama = 1 if instance.is_drama else 0
    # ※ modelにある他のジャンル（is_scifiなど）も同様に足せます

    # 最後に保存！
    showing.save()