# movies/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Movie, NowShowingMovie
from .apps import MoviesConfig
import pandas as pd

@receiver(post_save, sender=Movie)
def auto_fill_ai_data(sender, instance, created, **kwargs):
    if not MoviesConfig.ai_pack:
        return

    pack = MoviesConfig.ai_pack
    
    # 1. 紐づく全てのデータを取得（これで映画館ごとのデータが全部対象になる）
    showings = NowShowingMovie.objects.filter(movie=instance)
    if not showings.exists():
        # まだ NowShowingMovie が作られていなければ、何もしない（View側で作られるのを待つ）
        return

    # 2. AI予測用の数値を計算（代表で1回だけ計算する）
    d_rank = pack['rank_map'].get(instance.director_name, 0)
    c_rank = pack['comp_map'].get(instance.company, 0)
    s1 = pack['actor_map'].get(instance.cast1_name, 0)
    s2 = pack['actor_map'].get(instance.cast2_name, 0)
    s3 = pack['actor_map'].get(instance.cast3_name, 0)
    total_cast = s1 + s2 + s3
    
    # リリース月
    r_month = instance.release_date.month if instance.release_date else 1

    # AIモデルが求める特徴量を準備
    input_data = {col: 0 for col in pack['features']}
    input_data.update({
        'budget': float(instance.budget or 0),
        'release_month': r_month,
        'is_series': 1 if instance.is_series else 0,
        'director_rank': d_rank,
        'cast_total_score': total_cast,
        'company_rank': c_rank,
        'budget*cast': float(instance.budget or 0) * total_cast,
        'budget_relative_score': 1.0,
        'cast_relative_score': 1.0,
        'Action': 1 if instance.is_action else 0,
        'Adventure': 1 if instance.is_adventure else 0,
        'Animation': 1 if instance.is_animation else 0,
        'Fantasy': 1 if instance.is_fantasy else 0,
        'Drama': 1 if instance.is_drama else 0,
    })

    try:
        # 予測実行
        input_df = pd.DataFrame([input_data])[pack['features']]
        prediction = pack['model'].predict(input_df)[0]
        prediction_int = int(prediction)

        # 3. 見つかった全てのレコードをループで更新
        for showing in showings:
            showing.director_rank = d_rank
            showing.company_rank = c_rank
            showing.cast_total_score = total_cast
            showing.predicted_final_revenue = prediction_int
            showing.priority_rank = prediction_int  # ここで 999 を上書き
            showing.prediction_score = float(prediction)
            
            # 重要：これを False にしないとスケジュールに乗りません
            showing.is_ending_soon = False 
            
            if instance.release_date:
                showing.release_year = instance.release_date.year
                showing.release_month = instance.release_date.month

            showing.save()

        print(f"成功！ {instance.title} のAI予測とランキングを更新しました。")

    except Exception as e:
        print(f"予測エラー: {e}")
