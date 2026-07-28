from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import RuleForm
from .models import Rule
from SuperGroup.models import SuperGroup

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

    rules = Rule.objects.filter(
        user=request.user,
        active=True,
    ).select_related('super_group')

    return render(
        request,
        'admin/list_rules.html',
        {
            'rules': rules,
            'form': form,
            'super_groups': SuperGroup.objects.order_by('name'),
            'open_rule_modal': request.method == 'POST' and form.errors,
        },
    )


@login_required
@require_POST
def edit_rule(request, id):
    rule = get_object_or_404(Rule, id=id, user=request.user, active=True)
    form = RuleForm(request.POST, instance=rule)
    if form.is_valid():
        form.save()
        messages.success(request, 'La regla se ha actualizado correctamente.')
    else:
        error = next(iter(form.errors.values()))[0]
        messages.error(request, f'No se pudo actualizar la regla: {error}')
    return redirect('list_rules')


@login_required
@require_POST
def deactivate_rule(request, id):
    rule = get_object_or_404(Rule, id=id, user=request.user, active=True)
    rule.active = False
    rule.save(update_fields=['active'])
    messages.success(request, 'La regla se ha desactivado correctamente.')
    return redirect('list_rules')


@login_required
@require_POST
def deactivate_rules_bulk(request):
    rule_ids = request.POST.getlist('selected_rules')
    count = Rule.objects.filter(
        id__in=rule_ids,
        user=request.user,
        active=True,
    ).update(active=False)

    if count:
        messages.success(request, f'{count} regla(s) desactivada(s) correctamente.')
    else:
        messages.warning(request, 'No se seleccionaron reglas válidas para desactivar.')
    return redirect('list_rules')


@login_required
def list_deactivated_rules(request):
    rules = Rule.objects.filter(
        user=request.user,
        active=False,
    ).select_related('super_group')
    return render(
        request,
        'admin/list_deactivated_rules.html',
        {'rules': rules},
    )


@login_required
@require_POST
def reactivate_rule(request, id):
    rule = get_object_or_404(Rule, id=id, user=request.user, active=False)
    rule.active = True
    rule.save(update_fields=['active'])
    messages.success(request, 'La regla se ha reactivado correctamente.')
    return redirect('list_deactivated_rules')


@login_required
@require_POST
def delete_rule(request, id):
    rule = get_object_or_404(Rule, id=id, user=request.user, active=False)
    rule.delete()
    messages.success(request, 'La regla se ha eliminado definitivamente.')
    return redirect('list_deactivated_rules')


@login_required
@require_POST
def reactivate_rules_bulk(request):
    rule_ids = request.POST.getlist('selected_rules')
    count = Rule.objects.filter(
        id__in=rule_ids,
        user=request.user,
        active=False,
    ).update(active=True)
    if count:
        messages.success(request, f'{count} regla(s) reactivada(s) correctamente.')
    else:
        messages.warning(request, 'No se seleccionaron reglas válidas para reactivar.')
    return redirect('list_deactivated_rules')


@login_required
@require_POST
def delete_rules_bulk(request):
    rule_ids = request.POST.getlist('selected_rules')
    queryset = Rule.objects.filter(
        id__in=rule_ids,
        user=request.user,
        active=False,
    )
    count = queryset.count()
    queryset.delete()
    if count:
        messages.success(request, f'{count} regla(s) eliminada(s) definitivamente.')
    else:
        messages.warning(request, 'No se seleccionaron reglas válidas para eliminar.')
    return redirect('list_deactivated_rules')
