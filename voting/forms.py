from django import forms
from .models import Voting

class VotingForm(forms.ModelForm):
    class Meta:
        model = Voting
        fields = ['title', 'description', 'start_date', 'end_date', 'voting_type', 'rules_file']
        
        # Виджеты нужны, чтобы в браузере появились удобные календарики
        widgets = {
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'voting_type': forms.Select(attrs={'class': 'form-control'}),
        }