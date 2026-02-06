from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('admin_Top/', views.AdminTopView.as_view(), name='admin_Top'),
    path('manager_Top/', views.ManagerTopView.as_view(), name='manager_Top'),
    path('create_manager/', views.ManagerCreateView.as_view(), name='manager_create'),
    path('managers/', views.ManagerListView.as_view(), name='manager_list'),
    path('managers/<int:pk>/edit-theater/', views.ManagerTheaterUpdateView.as_view(), name='manager_theater_update'),
    path('managers/<int:pk>/delete/', views.ManagerDeleteView.as_view(), name='manager_delete'),
    path('managers/<int:pk>/edit-theater/', views.ManagerTheaterUpdateView.as_view(), name='manager_theater_update'),
    path('setup-admin/', views.AdminRegistrationView.as_view(), name='admin_registration'),
    path('logout/', views.MyLogoutView.as_view(), name='logout'),
    path('password-change-force/', views.ForcePasswordChangeView.as_view(), name='password_change_force'),
    path('manager/top/', views.ManagerTopView.as_view(), name='manager_Top'),
]