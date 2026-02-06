from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import Theater, Screen, TheaterAssignment, TheaterManager
from accounts.views import AdminOnlyMixin
from accounts.models import ManagerProfile 

# --- 管理人：映画館の基本登録 ---
class TheaterCreateView(LoginRequiredMixin, AdminOnlyMixin, CreateView):
    model = Theater
    template_name = 'theaters/theater_create.html' 
    fields = ['name', 'address', 'total_screens'] 
    
    def get_success_url(self):
        return reverse_lazy('theaters:screen_setup', kwargs={'pk': self.object.pk})

class TheaterListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Theater
    template_name = 'theaters/theater_list.html'
    context_object_name = 'theaters'

class TheaterDeleteView(LoginRequiredMixin, AdminOnlyMixin, View):
    def get(self, request, *args, **kwargs):
        theater = get_object_or_404(Theater, pk=kwargs.get('pk'))
        theater.delete()
        return redirect('theaters:theater_list')

# --- 管理人：各シアター（スクリーン）の登録 ---
class ScreenSetupView(LoginRequiredMixin, AdminOnlyMixin, View):
    def get(self, request, pk):
        theater = get_object_or_404(Theater, pk=pk)
        screen_range = range(1, theater.total_screens + 1)
        return render(request, 'theaters/screen_setup.html', {
            'theater': theater,
            'screen_range': screen_range
        })

    def post(self, request, pk):
        theater = get_object_or_404(Theater, pk=pk)
        for i in range(1, theater.total_screens + 1):
            cap = request.POST.get(f'capacity_{i}')
            size = request.POST.get(f'size_{i}')
            Screen.objects.create(
                theater=theater,
                screen_number=i,
                capacity=cap,
                screen_size=size
            )
        return redirect('theaters:theater_list')

# --- 管理人：詳細・担当者確認 ---
class TheaterDetailView(LoginRequiredMixin, AdminOnlyMixin, DetailView):
    model = Theater
    template_name = 'theaters/theater_detail.html'
    context_object_name = 'theater'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['screens'] = self.object.screens.all().order_by('screen_number')
        return context

class TheaterManagerListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = ManagerProfile
    template_name = 'theaters/theater_manager_list.html'
    context_object_name = 'managers'

    def get_queryset(self):
        return ManagerProfile.objects.filter(theater_id=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['theater'] = get_object_or_404(Theater, pk=self.kwargs.get('pk'))
        return context

# --- 支配人：自分の担当劇場のスクリーン一覧 ---
class MyTheaterListView(LoginRequiredMixin, ListView):
    model = Screen
    template_name = 'theaters/my_theater_list.html'
    context_object_name = 'screens'

    def get_queryset(self):
        # 自分が「TheaterManager」か「TheaterAssignment」に登録されている映画館のIDを合体
        ids1 = TheaterManager.objects.filter(user=self.request.user).values_list('theater', flat=True)
        ids2 = TheaterAssignment.objects.filter(user=self.request.user).values_list('theater', flat=True)
        all_ids = list(ids1) + list(ids2)
        
        return Screen.objects.filter(theater__id__in=all_ids).order_by('screen_number')