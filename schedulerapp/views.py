import os
import pickle
import pandas as pd
from django.shortcuts import render
from django.views.generic import TemplateView
from django.conf import settings


class Top_pageView(TemplateView):
    template_name = 'schedulerapp/Top.html'

class PredictorView(TemplateView):
    template_name = 'schedulerapp/movie_Register.html'

    # 映画の売り上げ予測の変数を作成
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['result'] = None
        return context


    def post(self, request, *args, **kwargs):
        # モデル、監督、キャスト情報と接続
        path = os.path.join(settings.BASE_DIR, 'cinema_pack.pkl')
        # モデルが見つからない場合
        if not os.path.exists(path):
            return render(request, self.template_name, {'result': 'cinema_pack.pklが見つかりません'})

        # 接続したデータを読み取り専用で使用可能にする
        with open(path, 'rb') as f:
            pack = pickle.load(f)

        # 監督情報の受け取り
        d_name = request.POST.get('director_name')
        # キャスト情報の受け取り
        c_names = [
            request.POST.get('cast_name1'),
            request.POST.get('cast_name2'),
            request.POST.get('cast_name3')
        ]
        # 制作会社情報の受け取り
        comp_name = request.POST.get('company_name')
        # 数値入力、数字以外の入力だった場合それぞれ0,1を代入
        try:
            # 予算
            budget = float(request.POST.get('budget', 0))
            # 公開月
            month = int(request.POST.get('release_month', 1))
        except ValueError:
            budget, month = 0, 1

        # シリーズものか判定,1はシリーズ
        is_series = 1 if request.POST.get('is_series') else 0
        # ジャンル情報の受け取り
        genre_selected = request.POST.get('genre')

        # 監督情報をランク表と照らし合わせランクを割り出す
        d_rank = pack['rank_map'].get(d_name, 0)
        # 3人の出演映画の売り上げの合計をランクデータと照らし合わせる
        c_score = sum([pack['actor_map'].get(name, 0) for name in c_names if name])
        # 制作会社のランクを割り出す
        comp_rank = pack['comp_map'].get(comp_name, 0)

        # AI用データ作成
        # 情報を渡すひな形作成
        input_dict = {col: 0 for col in pack['features']}
        # 情報登録
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
        # 選んだジャンルだけ1に変える
        if genre_selected in input_dict:
            input_dict[genre_selected] = 1

        # 予測実行
        # データフレーム型に変える
        input_df = pd.DataFrame([input_dict])[pack['features']]
        # モデルにデータを渡す
        pred = pack['model'].predict(input_df)[0]
        # 予測結果を変数に格納
        result = "{:,} ドル".format(int(pred))
        return render(request, self.template_name, {'result': result})