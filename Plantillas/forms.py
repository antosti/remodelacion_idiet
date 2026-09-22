from django import forms

from .models import Rule, Template


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
            'frequency': forms.Select(attrs={'class': INPUT_CLASSES}),
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


class TemplateForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ('name', 'daily_kcal')
        labels = {
            'name': 'Nombre',
            'daily_kcal': 'Kcal diarias',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'daily_kcal': forms.NumberInput(
                attrs={'class': INPUT_CLASSES, 'min': '1', 'max': '10000', 'step': '1'}
            ),
        }

    def clean_daily_kcal(self):
        # Mismo rango que Plantillas.views.create_template, para que editar
        # una plantilla ya creada no pueda saltarse el limite impuesto al
        # crearla.
        daily_kcal = self.cleaned_data['daily_kcal']
        if daily_kcal <= 0 or daily_kcal > 10000:
            raise forms.ValidationError('Indica unas kcal diarias válidas (entre 1 y 10000).')
        return daily_kcal
