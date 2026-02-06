from django.contrib import admin
from django.urls import path, include
from accounts.views import MyLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', MyLoginView.as_view(), name='login_top'),
    path('accounts/', include('accounts.urls')),
    path('schedulerapp', include('schedulerapp.urls')),
    path('theaters/', include('theaters.urls', namespace='theaters')), 
    path('movies/', include('movies.urls')),
]