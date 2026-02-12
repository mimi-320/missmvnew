import os
import pickle
import pandas as pd
from datetime import datetime
 
from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
 
from .utils import fill_contract_schedules
from .models import Schedule
from movies.models import Movie, NowShowingMovie
from .utils import create_weekly_schedule
 
# --- トップページ ---
class Top_pageView(TemplateView):
    template_name = 'schedulerapp/Top.html'
 
# --- AI予測 & 自分の映画館への登録 ---
class PredictorView(TemplateView):
    template_name = 'schedulerapp/movie_Register.html'
 
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['result'] = None
        return context
 
    def post(self, request, *args, **kwargs):
        # 1. 学習済みモデル(pickle)の読み込み
        path = os.path.join(settings.BASE_DIR, 'cinema_pack.pkl')
        if not os.path.exists(path):
            return render(request, self.template_name, {'result': 'cinema_pack.pklが見つかりません'})
 
        with open(path, 'rb') as f:
            pack = pickle.load(f)
 
        # 2. 画面からの入力（タイトル、監督、予算など）
        movie_title = request.POST.get('title')
        d_name = request.POST.get('director_name')
        c_names = [
            request.POST.get('cast_name1'),
            request.POST.get('cast_name2'),
            request.POST.get('cast_name3')
        ]
        comp_name = request.POST.get('company_name')
 
        try:
            budget = float(request.POST.get('budget', 0))
            month = int(request.POST.get('release_month', 1))
        except ValueError:
            budget, month = 0, 1
 
        is_series = 1 if request.POST.get('is_series') else 0
        genre_selected = request.POST.get('genre')
 
        # 3. 特徴量の計算（AIモデル用）
        d_rank = pack['rank_map'].get(d_name, 0)
        c_score = sum([pack['actor_map'].get(name, 0) for name in c_names if name])
        comp_rank = pack['comp_map'].get(comp_name, 0)
 
        input_dict = {col: 0 for col in pack['features']}
        input_dict.update({
            'budget': budget,
            'release_month': month,
            'is_series': is_series,
            'director_rank': d_rank,
            'cast_total_score': c_score,
            'company_rank': comp_rank,
            'budget*cast': budget * c_score,
            'budget_relative_score': 1.0,
            'cast_relative_score': 1.0,
        })
        if genre_selected in input_dict:
            input_dict[genre_selected] = 1
 
        # 4. 予測実行
        input_df = pd.DataFrame([input_dict])[pack['features']]
        pred = pack['model'].predict(input_df)[0]
        prediction_value = int(pred)
 
        # 自分の映画館のデータとしてデータベースに保存
        if movie_title:
            try:
                # ログインしているユーザーの映画館を取得
                my_theater = request.user.manager_profile.theater
                # 元の映画マスタを取得
                movie_obj = Movie.objects.filter(title=movie_title).first()
               
                if movie_obj:
                    # 「映画」×「自分の映画館」で上映中映画データを作成/更新
                    now_showing, created = NowShowingMovie.objects.get_or_create(
                        movie=movie_obj,
                        theater=my_theater
                    )
                   
                    # 予測値と計算用パラメータを保存
                    now_showing.predicted_final_revenue = prediction_value
                    now_showing.prediction_score = prediction_value  # スコア計算用
                    now_showing.company_rank = comp_rank
                    now_showing.director_rank = d_rank
                    now_showing.cast_total_score = c_score
                    now_showing.release_month = month
                    now_showing.save()
            except Exception as e:
                print(f"DB保存エラー: {e}")

        result = "{:,} ドル".format(prediction_value)
        return render(request, self.template_name, {'result': result})
# schedulerapp/views.py

def schedule_weekly_generate_view(request):
    reports = None # 初期状態
    
    if request.method == "POST":
        target_date = request.POST.get('target_date') # HTMLの <input name="target_date"> から取得
        
        if not target_date:
            from django.contrib import messages
            messages.error(request, "開始日を選択してください。")
        else:
            # ここで 1週間ループ関数を起動！
            reports = create_weekly_schedule(target_date, request.user)
    
    return render(request, 'schedulerapp/generate.html', {
        'reports': reports
    })

def schedule_list_view(request):
    my_theater = request.user.manager_profile.theater
    target_date_str = request.GET.get('date')

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = datetime.now().date()
    else:
        target_date = datetime.now().date()
 
    # 1. 普通にスケジュールを取得
    schedules = Schedule.objects.filter(
        screen__theater=my_theater,
        start_time__date=target_date
    ).order_by('movie', 'start_time')
 
    # 2. 【ここが重要！】映画ごとに上映時間をまとめる
    movie_schedules = {}
    for s in schedules:
        movie = s.movie
        if movie not in movie_schedules:
            movie_schedules[movie] = []
        movie_schedules[movie].append(s)
 
    return render(request, 'schedulerapp/list.html', {
        'movie_schedules': movie_schedules, # まとめたデータを渡す
        'target_date': target_date,
    })