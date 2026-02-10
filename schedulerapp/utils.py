from datetime import datetime, time, timedelta
from django.db.models import Max
from .models import Schedule, ScheduleTemplate
from theaters.models import Screen
from movies.models import DistributionContract, NowShowingMovie

# --- ① スコア計算（売上トレンドを数値化） ---
def calculate_priority_score(showing_movie, target_date):
    days_since = (target_date - showing_movie.movie.release_date).days
    week_num = (days_since // 7) + 1
    
    base_score = showing_movie.predicted_final_revenue / 1000000 
    if base_score <= 0:
        base_score = showing_movie.prediction_score
    if base_score <= 0:
        base_score = 100.0

    score = base_score
    if showing_movie.is_ending_soon:
        return 0

    final_goal = showing_movie.predicted_final_revenue
    if week_num >= 2 and final_goal > 0 and showing_movie.current_revenue > 0:
        if week_num == 2:
            target_30 = final_goal * 0.3
            score *= (1.5 if showing_movie.current_revenue >= target_30 else 0.7)
        elif week_num <= 4:
            target_50 = final_goal * 0.5
            score *= (1.2 if showing_movie.current_revenue >= target_50 else 0.5)
    elif week_num > 4:
        score *= 0.3

    return score

# --- ② 補助関数（保存と空きチェック） ---
def save_slots_to_db(date, screen, movie, template):
    start_times = [t.strip() for t in template.start_times.split(',')]
    for start_str in start_times:
        hour, minute = map(int, start_str.split(':'))
        start_dt = datetime.combine(date, time(hour, minute))
        end_dt = start_dt + timedelta(minutes=movie.runtime)
        if not Schedule.objects.filter(screen=screen, start_time__lt=end_dt, end_time__gt=start_dt).exists():
            Schedule.objects.create(movie=movie, screen=screen, start_time=start_dt, end_time=end_dt)

def find_empty_screen(required_rank, target_date, my_theater, start_times, movie_runtime):
    screens = Screen.objects.filter(theater=my_theater).order_by('screen_rank')
    if required_rank:
        screens = screens.filter(screen_rank=required_rank)
        
    for screen in screens:
        all_slots_free = True
        for start_str in start_times:
            hour, minute = map(int, start_str.split(':'))
            start_dt = datetime.combine(target_date, time(hour, minute))
            end_dt = start_dt + timedelta(minutes=movie_runtime)
            if Schedule.objects.filter(screen=screen, start_time__lt=end_dt, end_time__gt=start_dt).exists():
                all_slots_free = False
                break
        if all_slots_free: return screen
    return None

# --- ③ 契約分（最低ノルマ）を埋める ---
def fill_mandatory_contracts(target_date, my_theater, screens, all_now_showing):
    run_counts = {}
    contracts = []

    for sm in all_now_showing:
        run_counts[sm.movie.id] = 0
        if hasattr(sm, 'distributioncontract'):
            c = sm.distributioncontract
            c.temp_score = calculate_priority_score(sm, target_date)
            contracts.append(c)

    contracts.sort(key=lambda x: (x.screening_type != 'exclusive', x.required_screen_rank is None, -x.temp_score))

    for c in contracts:
        movie_data = c.movie.movie
        # もし run_counts に映画IDが登録されていなければ、ここで 0 回として登録する
        if c.movie.id not in run_counts:
            run_counts[c.movie.id] = 0
        # -------------------------------

        template = ScheduleTemplate.objects.filter(limit_runtime__gte=movie_data.runtime).order_by('limit_runtime').first()
        if not template: continue

        if c.screening_type == 'exclusive':
            st_list = [t.strip() for t in template.start_times.split(',')]
            target_screen = find_empty_screen(c.required_screen_rank, target_date, my_theater, st_list, movie_data.runtime)
            if target_screen:
                save_slots_to_db(target_date, target_screen, movie_data, template)
                run_counts[c.movie.id] = len(st_list)
        else:
            needed = c.required_daily_runs or 0
            for scr in screens.order_by('screen_rank'):
                if run_counts[c.movie.id] >= needed: break
                st_list = [t.strip() for t in template.start_times.split(',')]
                for st in st_list:
                    if run_counts[c.movie.id] >= needed: break
                    hour, minute = map(int, st.split(':'))
                    start_dt = datetime.combine(target_date, time(hour, minute))
                    end_dt = start_dt + timedelta(minutes=movie_data.runtime)

                    # 全シアターの中で、同じ時間に同じ映画が「1つでも」あればスキップする
                    is_duplicated = Schedule.objects.filter(
                        movie=movie_data, 
                        start_time=start_dt
                    ).exists()

                    if is_duplicated:
                        continue # 別のシアターで同じ時間にやってるなら、このシアターは飛ばす

                    if not Schedule.objects.filter(screen=scr, start_time__lt=end_dt, end_time__gt=start_dt).exists():
                        Schedule.objects.create(movie=movie_data, screen=scr, start_time=start_dt, end_time=end_dt)
                        run_counts[c.movie.id] += 1
                        
    return run_counts

# --- ④ 追加（売上ランキング）分を埋める（10シアター全開放版） ---
def fill_extra_slots(target_date, my_theater, screens, run_counts, all_now_showing):
    # 1. スコア順に映画を並べる
    ranking = sorted(all_now_showing, key=lambda x: calculate_priority_score(x, target_date), reverse=True)
    
    # 2. 全てのスクリーン（10シアター分）を順番に見ていく
    for scr in screens.order_by('screen_rank'):
        # 各映画を順番に、このシアターに入れられるか試す
        for sm in ranking:
            movie_data = sm.movie
            
            # その映画に合うテンプレート（上映開始時間のセット）を探す
            template = ScheduleTemplate.objects.filter(limit_runtime__gte=movie_data.runtime).order_by('limit_runtime').first()
            if not template: continue
            
            st_list = [t.strip() for t in template.start_times.split(',')]
            
            for st in st_list:
                hour, minute = map(int, st.split(':'))
                start_dt = datetime.combine(target_date, time(hour, minute))
                end_dt = start_dt + timedelta(minutes=movie_data.runtime)

                # シアターが空いていて、かつ同じ時間に同じ映画が他でやっていなければ、即採用！
                if not Schedule.objects.filter(screen=scr, start_time__lt=end_dt, end_time__gt=start_dt).exists():
                    if not Schedule.objects.filter(movie=movie_data, start_time=start_dt).exists():
                        Schedule.objects.create(movie=movie_data, screen=scr, start_time=start_dt, end_time=end_dt)
                        run_counts[movie_data.id] = run_counts.get(movie_data.id, 0) + 1


# --- ⑤ 実行メイン処理 ---
def fill_contract_schedules(target_date, user):
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    try:
        my_theater = user.manager_profile.theater
        screens = Screen.objects.filter(theater=my_theater)
        Schedule.objects.filter(screen__theater=my_theater, start_time__date=target_date).delete()
        
        all_now_showing = NowShowingMovie.objects.filter(theater=my_theater)
        
        # 1. 契約（最低ライン）を埋める
        run_counts = fill_mandatory_contracts(target_date, my_theater, screens, all_now_showing)
        
        # 2. 追加（売上ランキング）で残りを埋める
        fill_extra_slots(target_date, my_theater, screens, run_counts, all_now_showing)
        
        return []
    except Exception as e:
        import traceback
        return [f"エラー発生: {str(e)}", traceback.format_exc()]

from django.utils import timezone 

def create_weekly_schedule(start_date_str, user):
    if isinstance(start_date_str, str):
        base_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
    else:
        base_dt = datetime.combine(start_date_str, time.min)

    total_reports = []

    # 2. 7回ループ
    for i in range(7):
        target_date = (base_dt + timedelta(days=i)).date()
        
        daily_errors = fill_contract_schedules(target_date, user)
        
        # レポート作成
        date_label = target_date.strftime('%m/%d(%a)')
        if not daily_errors:
            total_reports.append(f"{date_label}: 生成完了")
        else:
            total_reports.append(f"{date_label}: エラー({daily_errors[0]})")
            
    return total_reports