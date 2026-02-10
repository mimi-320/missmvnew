# movies/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Movie, NowShowingMovie
from .apps import MoviesConfig
import pandas as pd

# movies/signals.py

@receiver(post_save, sender=Movie)
def auto_fill_ai_data(sender, instance, created, **kwargs):
    # 1. AIパックの確認
    if not MoviesConfig.ai_pack:
        return

    pack = MoviesConfig.ai_pack
    
    # 2. データの箱（NowShowingMovie）を準備
    showing, _ = NowShowingMovie.objects.get_or_create(movie=instance)

    # 3. 各項目の埋め込み（中田さんのコードをここに集約）
    showing.director_rank = pack['rank_map'].get(instance.director_name, 0)
    showing.company_rank = pack['comp_map'].get(instance.company, 0)

    s1 = pack['actor_map'].get(instance.cast1_name, 0)
    s2 = pack['actor_map'].get(instance.cast2_name, 0)
    s3 = pack['actor_map'].get(instance.cast3_name, 0)
    showing.cast_total_score = s1 + s2 + s3

    if instance.release_date:
        showing.release_year = instance.release_date.year
        showing.release_month = instance.release_date.month

    showing.is_lang_ja = 1 if instance.language == 'ja' else 0
    showing.is_lang_en = 1 if instance.language == 'en' else 0

    showing.is_series = 1 if instance.is_series else 0
    showing.is_animation = 1 if instance.is_animation else 0
    showing.is_action = 1 if instance.is_action else 0
    showing.is_adventure = 1 if instance.is_adventure else 0
    showing.is_fantasy = 1 if instance.is_fantasy else 0
    showing.is_drama = 1 if instance.is_drama else 0

    # 4. AI予測用のデータ整理
    input_data = {
        'budget': float(instance.budget or 0),
        'release_month': showing.release_month,
        'is_series': showing.is_series,
        'director_rank': showing.director_rank,
        'cast_total_score': showing.cast_total_score,
        'company_rank': showing.company_rank,
        'budget*cast': float(instance.budget or 0) * showing.cast_total_score,
        'budget_relative_score': 1.0,
        'cast_relative_score': 1.0,
        'Adventure': showing.is_adventure,
        'Action': showing.is_action,
        'Animation': showing.is_animation,
        'Fantasy': showing.is_fantasy,
        'Drama': showing.is_drama,
    }
    
    # 5. 予測実行
    try:
        input_df = pd.DataFrame([input_data])[pack['features']]
        prediction = pack['model'].predict(input_df)[0]
        showing.predicted_final_revenue = int(prediction)
        
        # 💡 もし「計算後優先順位」という項目名が priority_rank なら、ここを上書きする！
        # これで 999 ではなく予測値が直接入ります。
        showing.priority_rank = int(prediction)
    except Exception as e:
        print(f"予測エラーが発生しました: {e}")
        showing.predicted_revenue = 0
        showing.prediction_score = 0.0

    showing.save()

@receiver(post_save, sender=Movie)
def auto_fill_ai_data(sender, instance, created, **kwargs):
    if not MoviesConfig.ai_pack:
        return

    pack = MoviesConfig.ai_pack
    # update_or_create を使って、確実に既存のデータを上書きするようにします
    showing, _ = NowShowingMovie.objects.get_or_create(movie=instance)

    # --- (中略：各種ランクの計算はそのまま) ---
    showing.director_rank = pack['rank_map'].get(instance.director_name, 0)
    showing.company_rank = pack['comp_map'].get(instance.company, 0)
    s1 = pack['actor_map'].get(instance.cast1_name, 0)
    s2 = pack['actor_map'].get(instance.cast2_name, 0)
    s3 = pack['actor_map'].get(instance.cast3_name, 0)
    showing.cast_total_score = s1 + s2 + s3
    
    if instance.release_date:
        showing.release_month = instance.release_date.month

    input_data = {col: 0 for col in pack['features']} 

    # --- 既存のデータを上書きして埋める ---
    input_data.update({
        'budget': float(instance.budget or 0),
        'release_month': showing.release_month or 1,
        'release_year': showing.release_year or 2026, # 追加
        'is_series': 1 if instance.is_series else 0,
        'director_rank': showing.director_rank,
        'cast_total_score': showing.cast_total_score,
        'company_rank': showing.company_rank,
        'budget*cast': float(instance.budget or 0) * showing.cast_total_score,
        'budget_relative_score': 1.0,
        'cast_relative_score': 1.0,
        
        # ジャンル (AIが求める名前に合わせる)
        'is_action': 1 if instance.is_action else 0,
        'is_adventure': 1 if instance.is_adventure else 0,
        'is_animation': 1 if instance.is_animation else 0,
        'is_fantasy': 1 if instance.is_fantasy else 0,
        'is_drama': 1 if instance.is_drama else 0,
        
        # 言語
        'ja': 1 if instance.language == 'ja' else 0,
        'en': 1 if instance.language == 'en' else 0,
    })

    # 💡 ライバル数などの足りない項目も「とりあえず0」で埋めることでエラーを回避
    # (AIモデルの features に含まれる全てのキーが input_data に存在する必要があります)

    try:
        # AIが求める順番に並べ替えてデータフレーム化
        input_df = pd.DataFrame([input_data])[pack['features']]
        prediction = pack['model'].predict(input_df)[0]
        
        prediction_int = int(prediction)
        showing.predicted_final_revenue = prediction_int
        showing.priority_rank = prediction_int  # これで 999 を撃退！
        showing.prediction_score = float(prediction) 
        
        print(f"成功！ {instance.title} の予測収入: {prediction_int}")

    except Exception as e:
        print(f"予測エラー: {e}")

    # 💡 最後にしっかり保存
    showing.save()