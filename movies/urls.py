from django.urls import path
from . import views
from .views import ContractCreateView

app_name = 'movies'

urlpatterns = [
    path('list/', views.MovieListView.as_view(), name='movie_list'),
    path('create/', views.MovieCreateView.as_view(), name='movie_create'),
    path('detail/<int:pk>/', views.MovieDetailView.as_view(), name='movie_detail'),
    path('contract/form/<int:movie_pk>/', views.ContractCreateView.as_view(), name='contract_form'),
    path('stop-showing/<int:pk>/', views.StopShowingView.as_view(), name='stop_showing'),
]
