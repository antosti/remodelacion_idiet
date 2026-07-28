from django import forms

from .models import Rule


INPUT_CLASSES = (
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-700 '
    'outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/30'
)


class RuleForm(forms.ModelForm):
    class Meta:
        model = Rule
        fields = ('super_group', 'min', 'max', 'frequency', 'level')
        labels = {
            'super_group': 'Grupo de alimentos',
            'min': 'Unidades mínimas',
            'max': 'Unidades máximas',
            'frequency': 'Frecuencia',
            'level': 'Nivel',
        }
        widgets = {
            'super_group': forms.Select(attrs={'class': INPUT_CLASSES}),
            'min': forms.NumberInput(
                attrs={'class': INPUT_CLASSES, 'min': '0', 'step': '0.01'}
            ),
            'max': forms.NumberInput(
                attrs={'class': INPUT_CLASSES, 'min': '0', 'step': '0.01'}
            ),
            'frequency': forms.NumberInput(
                attrs={'class': INPUT_CLASSES, 'min': '1', 'step': '1'}
            ),
            'level': forms.NumberInput(
                attrs={'class': INPUT_CLASSES, 'min': '1', 'step': '1'}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        minimum = cleaned_data.get('min')
        maximum = cleaned_data.get('max')
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error('max', 'El máximo debe ser mayor o igual que el mínimo.')
        return cleaned_data
