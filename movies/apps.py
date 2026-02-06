# movies/apps.py
from django.apps import AppConfig
from django.conf import settings
import pickle
import os

class MoviesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'movies'

    # AIパックをここに保管する変数
    ai_pack = None

    def ready(self):
        # サーバー起動時に1回だけ実行される
        if os.path.exists(settings.CINEMA_PACK_PATH):
            with open(settings.CINEMA_PACK_PATH, 'rb') as f:
                # クラス変数に保存して、どこからでも呼べるようにする
                MoviesConfig.ai_pack = pickle.load(f)
        
        # ここでシグナル（自動計算）を読み込む
        import movies.signals