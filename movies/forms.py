from django import forms
from .models import DistributionContract
from theaters.models import Screen  # 💡 シアター情報をインポート

class ContractForm(forms.ModelForm):
    # 初期化する時に「誰がログインしているか」を受け取って選択肢を変える
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # 1. ログイン中の支配人の映画館を特定
            my_theater = user.manager_profile.theater
            
            # 2. その映画館にある「実際に使われているランク」だけを取得
            existing_ranks = Screen.objects.filter(theater=my_theater)\
                                        .values_list('screen_rank', flat=True)\
                                        .distinct()\
                                        .order_by('screen_rank')

            # 3. セレクトボックスの選択肢を作り直す
            choices = [('', '--- 指定なし（どこでもOK） ---')]
            for r in existing_ranks:
                label = f"ランク{r}"
                if r == 1: label += "（大）"
                if r == 2: label += "（中）"
                if r == 3: label += "（小）"
                choices.append((r, label))
            
            # 4. フォームの選択肢を上書き！
            self.fields['required_screen_rank'].widget.choices = choices

    class Meta:
        model = DistributionContract
        fields = ['required_screen_rank', 'required_daily_runs', 'contract_period_weeks', 'screening_type', 'special_notes']
        widgets = {
            'required_screen_rank': forms.Select(attrs={'class': 'form-control'}),
            'screening_type': forms.Select(attrs={'class': 'form-control'}),
            'required_daily_runs': forms.NumberInput(attrs={'class': 'form-control'}),
            'contract_period_weeks': forms.NumberInput(attrs={'class': 'form-control'}),
            'special_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }