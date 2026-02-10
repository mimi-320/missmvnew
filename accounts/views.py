from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User,ManagerProfile
from theaters.models import Theater 
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import ListView, UpdateView
from django.views import View
from django.contrib.auth.views import LogoutView
from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin

# フォームを新しく定義する（UserCreationFormを継承して自分たちのモデルに合わせる）
class AdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User # あなたが定義したカスタムユーザーモデルを指定
        fields = ("username", "email") # 必要に応じて項目を増やす

class MyLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 管理人が一人もいないかチェックした結果をHTMLに送る
        context['no_admin'] = not User.objects.filter(is_top_admin=True).exists()
        return context

    def get_success_url(self):
        user = self.request.user

        # 1. 管理人の場合：そのまま管理人トップへ
        if user.is_top_admin:
            return reverse_lazy('accounts:admin_Top')

        # 2. 支配人の場合
        elif user.is_manager:
            #  モデルの needs_password_change フラグをチェック
            if user.manager_profile.needs_password_change:
                # 初回なら強制変更画面へ
                return reverse_lazy('accounts:password_change_force')
            else:
                # 2回目以降なら支配人トップへ
                return reverse_lazy('accounts:manager_Top')

        # 3. どちらでもない（一般ユーザーなど）はログインに戻す
        return reverse_lazy('accounts:login')

# ---  管理人判定 ---
class AdminOnlyMixin(UserPassesTestMixin):

    # 自身が管理人だったときだけプログラムを実行できる
    def test_func(self):
        # ログインしている、かつ is_top_admin が True の場合だけ許可
        return self.request.user.is_authenticated and self.request.user.is_top_admin

# ---  管理人トップ ---
class AdminTopView(LoginRequiredMixin, AdminOnlyMixin, TemplateView):
    template_name = 'accounts/admin_Top.html'

class ManagerCreationForm(UserCreationForm):
    theater = forms.ModelChoiceField(
        queryset=Theater.objects.all(), 
        label="担当する映画館",
        required=True,
        empty_label="映画館を選択してください"
    )

    class Meta(UserCreationForm.Meta,):
        model = User
        fields = ("username", "email", "theater")

# --- ログアウト ---
class MyLogoutView(LogoutView):
    next_page = reverse_lazy('accounts:login')

# ---  支配人作成View ---
class ManagerCreateView(LoginRequiredMixin, AdminOnlyMixin, CreateView):
    form_class = ManagerCreationForm
    template_name = 'accounts/manager_create.html'
    success_url = reverse_lazy('accounts:admin_Top')

    # 画面を表示する前に「映画館があるか」チェックする
    def get(self, request, *args, **kwargs):
        # もし映画館が1つも登録されていなかったら
        if not Theater.objects.exists():
            # 映画館登録ページ（theaters:theater_create）へ強制移動！
            return redirect('theaters:theater_create')
        
        # 映画館があれば、普通に支配人作成画面を表示する
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # ユーザー保存
        user = form.save(commit=False)
        user.is_manager = True
        user.save()

        # 映画館との紐付け
        selected_theater = form.cleaned_data['theater']
        ManagerProfile.objects.create(
            user=user,
            theater=selected_theater
        )
        return super().form_valid(form)

class ManagerListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = ManagerProfile
    template_name = 'accounts/manager_list.html'
    context_object_name = 'managers'

    def get_queryset(self):
        # 1. まずは全員取得
        queryset = ManagerProfile.objects.all()
        # 2. URLの?theater_id=... か、検索フォームからの値を受け取る
        theater_id = self.request.GET.get('theater_id')
        
        # 3. もし映画館IDが指定されていたら、その館の支配人だけに絞る
        if theater_id:
            queryset = queryset.filter(theater_id=theater_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 4. 検索ボックス（プルダウン）用に全映画館のリストを送る
        context['theaters'] = Theater.objects.all()
        # 5. 現在どの映画館で絞り込んでいるかをHTMLに伝える
        context['selected_theater'] = self.request.GET.get('theater_id')
        return context

# 映画館を後から紐付けるための編集画面
class ManagerTheaterUpdateView(LoginRequiredMixin, AdminOnlyMixin, UpdateView):
    model = ManagerProfile
    fields = ['theater']
    template_name = 'accounts/manager_theater_form.html'
    success_url = reverse_lazy('accounts:manager_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # self.get_object() で、今編集している支配人のデータ（Profile）が取れます
        # そのProfileに紐付いている「User（名前など）」を target_user としてHTMLに送ります
        context['target_user'] = self.get_object().user
        return context

# --- 支配人情報削除（シンプル版） ---
class ManagerDeleteView(LoginRequiredMixin, AdminOnlyMixin, View):
    def get(self, request, *args, **kwargs):
        # 1. URLから渡されたID（pk）でユーザーを特定
        user_id = kwargs.get('pk')
        try:
            # 2. 支配人フラグがあるユーザーを探して削除
            manager = User.objects.get(pk=user_id, is_manager=True)
            manager.delete()
            print(f"ID:{user_id} の支配人を削除しました") # ターミナルで確認用
        except User.DoesNotExist:
            print("削除対象が見つかりませんでした")

        # 3. 削除が終わったら、即座に一覧画面にリダイレクト（戻る）
        return redirect('accounts:manager_list')
    
# ---  支配人トップ ---
class ManagerTopView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/manager_Top.html'

# --- 初回限定：強制パスワード変更View ---
class ForcePasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'accounts/password_change_force.html'
    
    # パスワード変更が完了した後の移動先
    success_url = reverse_lazy('accounts:manager_Top')

    def form_valid(self, form):
        # パスワードを保存（ここで新しいパスワードに変わる）
        response = super().form_valid(form)
        
        #  ここで支配人プロフィールの「変更が必要フラグ」をオフにする
        profile = self.request.user.manager_profile
        profile.needs_password_change = False
        profile.save()
        
        messages.success(self.request, "パスワードが新しく設定されました。次回からこのパスワードを使用してください。")
        return response
    
class ManagerTopView(LoginRequiredMixin, TemplateView):
    template_name = 'accounts/manager_Top.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ログインしている支配人の「プロフィール」を取得
        # ※ Profileがない場合のエラーを防ぐため、 hasattr でチェックするとより安全です
        if hasattr(self.request.user, 'manager_profile'):
            context['theater'] = self.request.user.manager_profile.theater
        return context