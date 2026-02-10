from django.contrib import admin
from .models import Movie, NowShowingMovie, DistributionContract

@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    # 管理画面の一覧で見たい項目を並べます
    # タイトル、上映時間、公開日など、モデルで定義したフィールド名を指定してください
    list_display = ('title', 'runtime', 'release_date')
    
    # タイトルで検索できるようにします（算数が苦手でも、文字入力で探せて便利！）
    search_fields = ('title',)

@admin.register(NowShowingMovie)
class NowShowingMovieAdmin(admin.ModelAdmin):
    # タイトル、予想売上、優先順位などを表示
    list_display = ('get_title', 'priority_rank', 'current_week_num', 'is_ending_soon')
    
    # 関連しているMovieモデルのタイトルを表示するための工夫
    def get_title(self, obj):
        return obj.movie.title
    get_title.short_description = '映画タイトル'

#DistributionContract（配布契約）を登録
@admin.register(DistributionContract)
class DistributionContractAdmin(admin.ModelAdmin):
    list_display = ('get_title', 'screening_type', 'required_daily_runs', 'required_screen_rank')
    
    def get_title(self, obj):
        return obj.movie.movie.title
    get_title.short_description = '映画タイトル'