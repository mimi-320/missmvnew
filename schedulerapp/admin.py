from django.contrib import admin
from .models import Schedule, ScheduleTemplate

admin.site.register(Schedule)

# Schedule がすでに登録されている場合はスキップし、
# まだ登録されていない ScheduleTemplate だけを登録する
if not admin.site.is_registered(ScheduleTemplate):
    admin.site.register(ScheduleTemplate)

# もし Schedule も一応確認しておきたい場合はこう書けます
if not admin.site.is_registered(Schedule):
    admin.site.register(Schedule)