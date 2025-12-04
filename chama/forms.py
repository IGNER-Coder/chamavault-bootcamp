from django import forms
from .models import ChamaGroup

class ChamaCreationForm(forms.ModelForm):
    class Meta:
        model = ChamaGroup
        fields = ['name', 'chama_type', 'contribution_amount', 'contribution_day', 'late_penalty_fee']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg', 'placeholder': 'e.g. KCA Tech Squad'}),
            'chama_type': forms.Select(attrs={'class': 'w-full p-3 border rounded-lg'}),
            'contribution_amount': forms.NumberInput(attrs={'class': 'w-full p-3 border rounded-lg'}),
            'contribution_day': forms.NumberInput(attrs={'class': 'w-full p-3 border rounded-lg', 'min': 1, 'max': 31}),
            'late_penalty_fee': forms.NumberInput(attrs={'class': 'w-full p-3 border rounded-lg'}),
        }