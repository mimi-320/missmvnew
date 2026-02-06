from django.urls import path
from . import views  

app_name = 'schedulerapp'

urlpatterns = [
    # index（関数）ではなく、PredictorView（クラス）を呼び出すように変更
    path('', views.PredictorView.as_view(), name='index'),
]