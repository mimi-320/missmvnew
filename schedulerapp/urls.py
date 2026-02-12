from django.urls import path
from . import views  

app_name = 'schedulerapp'

urlpatterns = [
    # index（関数）ではなく、PredictorView（クラス）を呼び出すように変更
    path('', views.PredictorView.as_view(), name='index'),
    # 末尾の「_view」を消して、views.pyに書いた名前に合わせます
    path('generate/', views.schedule_weekly_generate_view, name='schedule_generate'),
    path('list/', views.schedule_list_view, name='schedule_list'),
]