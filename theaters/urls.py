from django.urls import path, include
from . import views

app_name = 'theaters'

urlpatterns = [
    path('create/', views.TheaterCreateView.as_view(), name='theater_create'),
    path('list/', views.TheaterListView.as_view(), name='theater_list'),
    path('<int:pk>/delete/', views.TheaterDeleteView.as_view(), name='theater_delete'),
    path('theater/create/', views.TheaterCreateView.as_view(), name='theater_create'),
    path('theater/<int:pk>/screens/', views.ScreenSetupView.as_view(), name='screen_setup'),
    path('theater/<int:pk>/', views.TheaterDetailView.as_view(), name='theater_detail'),
    path('theater/<int:pk>/managers/', views.TheaterManagerListView.as_view(), name='theater_manager_list'),
    path('my-theater/', views.MyTheaterListView.as_view(), name='my_theater_list'),
]