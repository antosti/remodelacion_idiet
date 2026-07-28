from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import RuleForm
from .models import Rule

# Create your views here.
def list_templates(request):
    return render(request, 'admin/list_templates.html')


@login_required
def list_rules(request):
    form = RuleForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        rule = form.save(commit=False)
        rule.user = request.user
        rule.save()
        messages.success(request, 'La regla se ha creado correctamente.')
        return redirect('list_rules')

    rules = Rule.objects.filter(user=request.user).select_related('super_group')

    return render(
        request,
        'admin/list_rules.html',
        {
            'rules': rules,
            'form': form,
            'open_rule_modal': request.method == 'POST' and form.errors,
        },
    )
