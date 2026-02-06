from django.shortcuts import render
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.urls import reverse
from django.views.generic import DetailView
from .models import Movie, NowShowingMovie
from django.shortcuts import get_object_or_404, redirect
from django.views import View

class MovieCreateView(CreateView):
    model = Movie
    fields = [
        'title', 'runtime', 'release_date', 'budget', 'company', 'language',
        'director_name', 'cast1_name', 'cast2_name', 'cast3_name',
        'is_series', 'is_animation', 'is_action', 'is_adventure', 'is_fantasy', 'is_drama'
    ]
    template_name = 'movies/movie_form.html'

    # 成功した時の飛び先を「今作った映画の詳細」にする
    def get_success_url(self):
        # instance が今登録した映画のデータです
        return reverse('movies:movie_detail', kwargs={'pk': self.object.pk})
    
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
        # 映画データと一緒に、AI計算済みのデータ(nowshowingmovie)もまとめて持ってくる
        return Movie.objects.all().prefetch_related('nowshowingmovie')