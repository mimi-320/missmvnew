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
        response = super().form_valid(form)
        my_theater = self.request.user.manager_profile.theater

        # 「ID」で判別して、自分の映画館に登録する
        # get_or_create なら、もし2回ボタンを押しちゃっても重複エラーになりません！
        NowShowingMovie.objects.get_or_create(
            movie=self.object, 
            theater=my_theater
        )
    
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