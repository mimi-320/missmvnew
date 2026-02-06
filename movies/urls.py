from django.urls import path
from . import views

app_name = 'movies'

urlpatterns = [
    path('list/', views.MovieListView.as_view(), name='movie_list'),
    path('create/', views.MovieCreateView.as_view(), name='movie_create'),
    path('detail/<int:pk>/', views.MovieDetailView.as_view(), name='movie_detail'),
]