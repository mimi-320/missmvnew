from django.shortcuts import render
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.urls import reverse
from django.views.generic import DetailView
from .models import Movie, NowShowingMovie
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from .models import DistributionContract
from .forms import ContractForm
from django.db.models import Prefetch 

class MovieCreateView(CreateView):
    model = Movie
    fields = [
        'title', 'runtime', 'release_date', 'budget', 'company', 'language',
        'director_name', 'cast1_name', 'cast2_name', 'cast3_name',
        'is_series', 'is_animation', 'is_action', 'is_adventure', 'is_fantasy', 'is_drama'
    ]
    template_name = 'movies/movie_form.html'

    def form_valid(self, form):
        # 1. まず映画本体を保存
        response = super().form_valid(form)
        movie = self.object
        my_theater = self.request.user.manager_profile.theater

        # 2. 上映情報を作成（または取得）
        showing, created = NowShowingMovie.objects.get_or_create(
            movie=movie, 
            theater=my_theater
        )

        # 3. 【ここが重要！】作成した直後に AI の計算を強制的に実行する
        from .apps import MoviesConfig
        import pandas as pd
        
        if MoviesConfig.ai_pack:
            pack = MoviesConfig.ai_pack
            try:
                # 特徴量の準備（signals.pyにある計算と同じもの）
                d_rank = pack['rank_map'].get(movie.director_name, 0)
                c_rank = pack['comp_map'].get(movie.company, 0)
                total_cast = (pack['actor_map'].get(movie.cast1_name, 0) + 
                              pack['actor_map'].get(movie.cast2_name, 0) + 
                              pack['actor_map'].get(movie.cast3_name, 0))

                input_data = {col: 0 for col in pack['features']}
                input_data.update({
                    'budget': float(movie.budget or 0),
                    'release_month': movie.release_date.month if movie.release_date else 1,
                    'is_series': 1 if movie.is_series else 0,
                    'director_rank': d_rank,
                    'cast_total_score': total_cast,
                    'company_rank': c_rank,
                    'budget*cast': float(movie.budget or 0) * total_cast,
                })

                input_df = pd.DataFrame([input_data])[pack['features']]
                prediction = int(pack['model'].predict(input_df)[0])

                # 4. 0 になる隙を与えず、ここで直接保存！
                showing.predicted_final_revenue = prediction
                showing.priority_rank = prediction
                showing.is_ending_soon = False  # ✅ 確実に上映対象にする
                showing.save()
                
            except Exception as e:
                print(f"Viewでの予測エラー: {e}")

        return response

    def get_success_url(self):
        return reverse('movies:contract_form', kwargs={'movie_pk': self.object.pk})
    
class MovieDetailView(DetailView):
    model = Movie
    template_name = 'movies/movie_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # AIが自動計算したデータを一緒に画面に送る
        context['ai_data'] = NowShowingMovie.objects.filter(movie=self.object).first()
        return context
    
class MovieListView(ListView):
    model = Movie
    template_name = 'movies/movie_list.html'
    context_object_name = 'movie_list'

    def get_queryset(self):
        my_theater = self.request.user.manager_profile.theater
        
        return Movie.objects.filter(
            now_showings__theater=my_theater 
        ).prefetch_related(
            Prefetch(
                'now_showings',             
                queryset=NowShowingMovie.objects.filter(theater=my_theater),
                to_attr='my_showing_data'
            )
        ).distinct().order_by('-id')

class ContractCreateView(CreateView):
    model = DistributionContract
    form_class = ContractForm
    template_name = 'movies/contract_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    # 画面を表示する前に「映画ID」をフォームに初期値として入れる
    def get_initial(self):
        initial = super().get_initial()
        initial['movie'] = self.kwargs.get('movie_pk')
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # URLにある movie_pk を使って映画の情報を取得
        context['target_movie'] = get_object_or_404(Movie, pk=self.kwargs.get('movie_pk'))
        return context
    
    def form_valid(self, form):
        my_theater = self.request.user.manager_profile.theater
        #URLの映画ID かつ 自分の映画館 の上映情報を取得
        form.instance.movie = get_object_or_404(
            NowShowingMovie, 
            movie_id=self.kwargs.get('movie_pk'),
            theater=my_theater # 他の館の契約を上書きしないように！
        )
        return super().form_valid(form)

    # 保存した後の戻り先
    def get_success_url(self):
        return reverse('movies:movie_list')
    
# 上映終了（テーブルから削除）処理
class StopShowingView(View):
    def post(self, request, pk):
        my_theater = request.user.manager_profile.theater
        movie_showing = get_object_or_404(NowShowingMovie, movie_id=pk, theater=my_theater)
        movie_showing.delete()
        return redirect('movies:movie_list')