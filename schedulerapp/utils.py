import traceback
from datetime import datetime, time, timedelta
from django.db.models import Max, F, Prefetch
from django.utils.timezone import make_aware
from .models import Schedule, ScheduleTemplate
from theaters.models import Screen
from movies.models import NowShowingMovie

# --- ① スコア計算（売上トレンドを数値化） ---
def calculate_priority_score(showing_movie, target_date):
    days_since = (target_date - showing_movie.movie.release_date).days
    week_num = (days_since // 7) + 1

    base_score = (showing_movie.predicted_final_revenue or 0) / 1000000
    if base_score <= 0:
        base_score = showing_movie.prediction_score or 100.0

    score = float(base_score)

    final_goal = showing_movie.predicted_final_revenue or 0
    current_rev = showing_movie.current_revenue or 0

    if week_num >= 2 and final_goal > 0 and current_rev > 0:
        if week_num == 2:
            target_30 = final_goal * 0.3
            score *= (1.5 if current_rev >= target_30 else 0.7)
        elif week_num <= 4:
            target_50 = final_goal * 0.5
            score *= (1.2 if current_rev >= target_50 else 0.5)
    elif week_num > 4:
        score *= 0.3

    return score

# --- ② 契約分を埋める（ノルマ優先） ---
def fill_mandatory_contracts(target_date, my_theater, screens, all_now_showing):
    run_counts = {}
    contracts = []
    CLEANING_TIME = 20 

    for sm in all_now_showing:
        run_counts[sm.id] = 0
        if hasattr(sm, 'distributioncontract'):
            c = sm.distributioncontract
            c.temp_score = calculate_priority_score(sm, target_date)
            contracts.append(c)

    contracts.sort(key=lambda x: (x.screening_type != 'exclusive', x.required_screen_rank is None, -x.temp_score))

    opening = my_theater.opening_time
    limit = my_theater.last_start_time

    for c in contracts:
        movie_data = c.movie.movie
        movie_now_id = c.movie.id
        
        template = ScheduleTemplate.objects.filter(limit_runtime__gte=500).first()
        if not template:
            template = ScheduleTemplate.objects.filter(limit_runtime__gte=movie_data.runtime).order_by('limit_runtime').first()
        if not template: continue

        if c.screening_type == 'exclusive':
            st_list = sorted([t.strip() for t in template.start_times.split(',') if len(t.strip()) == 5])
            valid_st_list = [st for st in st_list if opening <= datetime.strptime(st, '%H:%M').time() <= limit]
            
            target_screen = None
            potential_screens = screens.filter(screen_rank=c.required_screen_rank).order_by('screen_number')
            for scr in potential_screens:
                # 日付カラムでチェック
                if not Schedule.objects.filter(screen=scr, date=target_date).exists():
                    target_screen = scr
                    break
            
            if target_screen:
                next_at = make_aware(datetime.combine(target_date, opening))
                for st in valid_st_list:
                    curr_st = make_aware(datetime.combine(target_date, datetime.strptime(st, '%H:%M').time()))
                    if curr_st >= next_at:
                        end_dt = curr_st + timedelta(minutes=movie_data.runtime)
                        # 保存時に date を入れる
                        Schedule.objects.create(
                            movie=movie_data, 
                            screen=target_screen, 
                            date=target_date, 
                            start_time=curr_st, 
                            end_time=end_dt
                        )
                        run_counts[movie_now_id] = run_counts.get(movie_now_id, 0) + 1
                        next_at = end_dt + timedelta(minutes=CLEANING_TIME)
        else:
            needed = c.required_daily_runs or 1
            target_screens = screens
            if c.required_screen_rank:
                target_screens = screens.filter(screen_rank=c.required_screen_rank)
            
            for scr in target_screens.order_by('screen_number'):
                if run_counts.get(movie_now_id, 0) >= needed: break
                
                st_list = sorted([t.strip() for t in template.start_times.split(',') if len(t.strip()) == 5])
                for st in st_list:
                    if run_counts.get(movie_now_id, 0) >= needed: break
                    
                    curr_st = make_aware(datetime.combine(target_date, datetime.strptime(st, '%H:%M').time()))
                    if curr_st.time() < opening or curr_st.time() > limit: continue

                    buffer_end = curr_st + timedelta(minutes=movie_data.runtime + CLEANING_TIME)
                    # 日付カラムで空きチェック
                    if not Schedule.objects.filter(screen=scr, date=target_date, start_time__lt=buffer_end, end_time__gt=curr_st).exists():
                        # 日付カラムで重複チェック
                        if not Schedule.objects.filter(movie=movie_data, date=target_date, start_time=curr_st).exists():
                            Schedule.objects.create(
                                movie=movie_data, 
                                screen=scr, 
                                date=target_date,
                                start_time=curr_st, 
                                end_time=curr_st + timedelta(minutes=movie_data.runtime)
                            )
                            run_counts[movie_now_id] = run_counts.get(movie_now_id, 0) + 1
                                
    return run_counts

# --- ③ 追加枠を埋める ---
def fill_extra_slots(target_date, my_theater, screens, run_counts, all_now_showing):
    ranking = sorted(all_now_showing, key=lambda x: calculate_priority_score(x, target_date), reverse=True)
    extra_counts = {sm.id: 0 for sm in all_now_showing}
    
    CLEANING_TIME = 20
    opening = my_theater.opening_time
    limit = my_theater.last_start_time
    total_free_slots = screens.count() * 5 
    
    def get_dynamic_max(rank_index, total_slots):
        base_min = 1
        if rank_index == 0: bonus = int(total_slots * 0.15)
        elif rank_index == 1: bonus = int(total_slots * 0.125)
        elif rank_index == 2: bonus = int(total_slots * 0.10)
        elif rank_index == 3: bonus = int(total_slots * 0.07)
        else: bonus = int(total_slots * 0.03)
        return base_min + bonus

    for scr in screens.order_by('-capacity'):
        next_available_dt = make_aware(datetime.combine(target_date, opening))
        
        # 日付カラムでその日の最後の予定を探す
        last_sched = Schedule.objects.filter(screen=scr, date=target_date).order_by('end_time').last()
        if last_sched:
            next_available_dt = last_sched.end_time + timedelta(minutes=CLEANING_TIME)

        template = ScheduleTemplate.objects.filter(limit_runtime__gte=500).first()
        if not template: continue
        st_list = sorted([t.strip() for t in template.start_times.split(',') if len(t.strip()) == 5])

        for st in st_list:
            current_st_dt = make_aware(datetime.combine(target_date, datetime.strptime(st, '%H:%M').time()))

            if current_st_dt.time() > limit or current_st_dt < next_available_dt:
                continue

            for i, sm in enumerate(ranking):
                target_max = get_dynamic_max(i, total_free_slots)
                if extra_counts.get(sm.id, 0) >= target_max:
                    continue

                # 日付カラムで重複チェック
                if Schedule.objects.filter(movie=sm.movie, date=target_date, start_time=current_st_dt).exists():
                    continue

                duration = sm.movie.runtime + CLEANING_TIME
                end_with_cleaning = current_st_dt + timedelta(minutes=duration)
                
                # 日付カラムで空きチェック
                is_occupied = Schedule.objects.filter(
                    screen=scr,
                    date=target_date,
                    start_time__lt=end_with_cleaning,
                    end_time__gt=current_st_dt
                ).exists()

                if not is_occupied:
                    Schedule.objects.create(
                        movie=sm.movie,
                        screen=scr,
                        date=target_date,
                        start_time=current_st_dt,
                        end_time=current_st_dt + timedelta(minutes=sm.movie.runtime)
                    )
                    extra_counts[sm.id] += 1
                    next_available_dt = current_st_dt + timedelta(minutes=sm.movie.runtime + CLEANING_TIME)
                    break

# --- ④ メイン処理 ---
def fill_contract_schedules(target_date, user):
    if isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    try:
        my_theater = user.manager_profile.theater
        screens = Screen.objects.filter(theater=my_theater)
        
        # 日付カラムで削除
        Schedule.objects.filter(screen__theater=my_theater, date=target_date).delete()

        all_now_showing = NowShowingMovie.objects.filter(theater=my_theater)

        run_counts = fill_mandatory_contracts(target_date, my_theater, screens, all_now_showing)
        fill_extra_slots(target_date, my_theater, screens, run_counts, all_now_showing)

        return []
    except Exception as e:
        return [f"エラー発生: {str(e)}", traceback.format_exc()]

# --- ⑤ 1週間生成メイン ---
def create_weekly_schedule(start_date_str, user):

    if isinstance(start_date_str, str):
        current_day = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        current_day = start_date_str

    total_reports = []

    for i in range(7):
        print(i)
        target_date = current_day + timedelta(days=i)
        print(f"--- ループ {i+1}回目: {target_date} を生成中 ---")

        daily_errors = fill_contract_schedules(target_date, user)
        
        date_label = target_date.strftime('%m/%d(%a)')
        if not daily_errors:
            total_reports.append(f"{date_label}: 生成完了")
        else:
            total_reports.append(f"{date_label}: エラー({daily_errors[0]})")
            print(f"エラー発生: {daily_errors}")

    return total_reports