import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, DecimalField, F, Q, Sum, Value, When
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import RuleForm, TemplateForm
from .models import Rule, Template, TemplateIntake
from Dishes.models import Dish
from Dishes.views import calculate_dish_nutrition
from idiet.permissions import scoped_queryset
from idiet.views import paginate_queryset
from Menus.generator.domain import MealSlotConfig, ROLE_LABELS
from Menus.generator.meal_structure import get_meal_structure
from Menus.generator.pools import ROLE_TO_DISH_TYPES
from SuperGroup.models import SuperGroup

# Orden de filas del calendario de una plantilla, igual que
# Menus.views.CANONICAL_ALIAS_ORDER (mismos intake_alias que genera esta app,
# ver create_template). Se duplica aqui en vez de importarla de Menus para no
# acoplar Plantillas a Menus; si algun dia el orden canonico cambia, hay que
# actualizar ambas constantes.
CANONICAL_ALIAS_ORDER = [
    'Desayuno', 'Media mañana',
    'Entrante - Comida', 'Plato principal - Comida', 'Postre - Comida',
    'Merienda',
    'Entrante - Cena', 'Plato principal - Cena', 'Postre - Cena',
    'Recena', 'Otros',
]

# Duracion fija de toda plantilla nueva: el usuario ya no elige los dias,
# solo el nombre y las tomas. La columna Template.duration se sigue usando
# tal cual (7 dias = 1 semana).
TEMPLATE_DURATION_DAYS = 7

# Expresion reutilizada por list_templates/list_deactivated_templates para
# anotar la media de kcal/dia a partir de las TemplateIntake asignadas
# (Template.daily_kcal ya no se usa para esto, ver create_template).
AVG_DAILY_KCAL_ANNOTATION = Case(
    When(duration__gt=0, then=Coalesce(Sum('templateintake__kcal'), Value(0)) / F('duration')),
    default=Value(0),
    output_field=DecimalField(max_digits=10, decimal_places=2),
)


def _meal_slots_from_post(post, standalone, groups):
    """Construye la lista de MealSlotConfig seleccionadas en el wizard de
    creacion de plantilla, con el mismo parsing de campos que
    Menus.views.build_diet_config_from_post (sin target ni fechas: una
    plantilla no tiene objetivo nutricional ni fecha de inicio, solo la
    estructura de tomas)."""
    standalone_by_id = {str(intake.id): intake for intake in standalone}
    meal_slots = []

    for intake_id in post.getlist('standalone_intakes'):
        intake = standalone_by_id.get(intake_id)
        if intake:
            meal_slots.append(MealSlotConfig(
                key=f'single-{intake.id}',
                label=intake.name,
                kind='single',
                intakes={'single': intake},
            ))

    for group_key, group_intakes in groups.items():
        if post.get(f'include_{group_key}') != 'on':
            continue

        include_starter = post.get(f'platos_{group_key}') == '2' and group_intakes.get('starter') is not None
        include_dessert = post.get(f'postre_{group_key}') == 'on' and group_intakes.get('dessert') is not None

        meal_slots.append(MealSlotConfig(
            key=f'group-{group_key}',
            label=group_key.capitalize(),
            kind='group',
            intakes=group_intakes,
            include_starter=include_starter,
            include_dessert=include_dessert,
        ))

    return meal_slots


def _dish_options_for_intake(user, intake):
    """Platos candidatos para una toma de plantilla: mismo criterio de rol/
    ingesta que Menus.views._dish_options_for_intake, pero sin las
    exclusiones de cliente (una plantilla no esta asociada a ningun
    cliente todavia)."""
    dish_types = ROLE_TO_DISH_TYPES.get(intake.course_role, [Dish.DishType.MAIN, Dish.DishType.SINGLE])
    qs = Dish.objects.filter(active=True, dish_type__in=dish_types)
    qs = qs.filter(Q(intakes__isnull=True) | Q(intakes=intake)).distinct()
    qs = scoped_queryset(qs, user, include_unassigned=True)
    return qs.order_by('name')


def _intake_nutrition(nutrition, quantity):
    factor = Decimal(quantity) / Decimal('100')
    return {
        'kcal': Decimal(str(nutrition['kcal_100g'])) * factor,
        'prot': round(Decimal(str(nutrition['protein_100g'])) * factor, 1),
        'fat': round(Decimal(str(nutrition['fat_100g'])) * factor, 1),
        'carb': round(Decimal(str(nutrition['carbs_100g'])) * factor, 1),
    }


@login_required
def list_templates(request):
    templates = scoped_queryset(Template.objects.filter(active=True), request.user).order_by('name')
    templates = templates.annotate(avg_daily_kcal=AVG_DAILY_KCAL_ANNOTATION)
    pagination = paginate_queryset(request, templates, per_page=10)

    return render(request, 'admin/list_templates.html', {
        'templates': pagination['page_obj'],
        'page_obj': pagination['page_obj'],
        'page_url_prefix': pagination['page_url_prefix'],
    })


@login_required
def create_template(request):
    standalone, groups = get_meal_structure()

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()

        error = None
        if not name:
            error = 'Indica un nombre para la plantilla.'

        meal_slots = _meal_slots_from_post(request.POST, standalone, groups) if not error else []
        if not error and not meal_slots:
            error = 'Selecciona al menos una toma para la plantilla.'

        if error:
            messages.error(request, error)
            return render(request, 'admin/create_template.html', {
                'standalone': standalone, 'groups': groups,
            })

        with transaction.atomic():
            # daily_kcal es NOT NULL en BD pero ya no se rellena desde el
            # formulario: el kcal/dia mostrado en la UI se calcula a partir
            # de las TemplateIntake asignadas (ver AVG_DAILY_KCAL_ANNOTATION
            # y template_detail).
            template = Template.objects.create(
                user=request.user,
                name=name,
                daily_kcal=0,
                duration=TEMPLATE_DURATION_DAYS,
            )

            rows = []
            for day_index in range(TEMPLATE_DURATION_DAYS):
                for slot in meal_slots:
                    for role in slot.active_roles():
                        alias = slot.label if slot.kind == 'single' else f'{ROLE_LABELS[role]} - {slot.label}'
                        rows.append(TemplateIntake(
                            template=template,
                            dish=None,
                            intake=slot.intakes[role],
                            quantity=0,
                            kcal=Decimal('0'),
                            menu_day=day_index,
                            intake_alias=alias,
                            is_free_meal=False,
                        ))
            TemplateIntake.objects.bulk_create(rows)

        messages.success(request, 'La plantilla se ha creado correctamente.')
        return redirect('template_detail', id=template.id)

    return render(request, 'admin/create_template.html', {
        'standalone': standalone,
        'groups': groups,
    })


@login_required
def template_detail(request, id):
    template = get_object_or_404(scoped_queryset(Template.objects.all(), request.user), id=id)

    items = list(TemplateIntake.objects.filter(template=template).select_related('dish', 'intake'))

    nutrition_cache = {}

    def nutrition_for(dish):
        if dish.id not in nutrition_cache:
            nutrition_cache[dish.id] = calculate_dish_nutrition(dish)
        return nutrition_cache[dish.id]

    cells = {}
    day_totals = {}
    for item in items:
        if item.dish_id is None:
            item.prot_total = item.fat_total = item.carb_total = Decimal('0')
        else:
            nutrition = nutrition_for(item.dish)
            totals_for_item = _intake_nutrition(nutrition, item.quantity)
            item.prot_total = totals_for_item['prot']
            item.fat_total = totals_for_item['fat']
            item.carb_total = totals_for_item['carb']

        cells[(item.menu_day, item.intake_alias)] = item

        totals = day_totals.setdefault(item.menu_day, {
            'kcal': Decimal('0'), 'prot': Decimal('0'), 'fat': Decimal('0'), 'carb': Decimal('0'),
        })
        totals['kcal'] += item.kcal
        totals['prot'] += item.prot_total
        totals['fat'] += item.fat_total
        totals['carb'] += item.carb_total

    known_aliases = {alias for _, alias in cells}
    row_aliases = [alias for alias in CANONICAL_ALIAS_ORDER if alias in known_aliases]
    row_aliases += sorted(known_aliases - set(row_aliases))

    # Sin fecha de inicio real: se agrupan los dias relativos (0..duration-1)
    # en bloques de 7 ("Semana N"), y cada dia se etiqueta "Dia N" en vez de
    # un nombre de dia de la semana real (ver diet_detail para el equivalente
    # con fechas de calendario).
    weeks = []
    day_index = 0
    while day_index < template.duration:
        days_info = []
        for offset in range(7):
            if day_index >= template.duration:
                break
            days_info.append({
                'day_index': day_index,
                'day_label': f'Día {day_index + 1}',
                'totals': day_totals.get(day_index),
            })
            day_index += 1

        week_rows = [
            {
                'alias': alias,
                'cells': [
                    {'day_index': day['day_index'], 'item': cells.get((day['day_index'], alias))}
                    for day in days_info
                ],
            }
            for alias in row_aliases
        ]

        weeks.append({'days': days_info, 'rows': week_rows})

    total_kcal = sum((totals['kcal'] for totals in day_totals.values()), Decimal('0'))
    avg_daily_kcal = total_kcal / template.duration if template.duration else Decimal('0')

    return render(request, 'admin/template_detail.html', {
        'template': template,
        'weeks': weeks,
        'avg_daily_kcal': avg_daily_kcal,
    })


@login_required
@require_POST
def edit_template(request, id):
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=True), request.user), id=id)
    form = TemplateForm(request.POST, instance=template)
    if form.is_valid():
        form.save()
        messages.success(request, 'La plantilla se ha actualizado correctamente.')
    else:
        error = next(iter(form.errors.values()))[0]
        messages.error(request, f'No se pudo actualizar la plantilla: {error}')
    return redirect('list_templates')


@login_required
@require_http_methods(['GET', 'POST'])
def edit_template_intake(request, template_id, item_id):
    """Editar una unica toma (plato + cantidad) de una plantilla, sin tocar
    el resto. Mismo contrato JSON que Menus.views.edit_menu_intake."""
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=True), request.user), id=template_id)
    item = get_object_or_404(
        TemplateIntake.objects.select_related('dish', 'intake'), id=item_id, template=template,
    )

    dish_options = list(_dish_options_for_intake(request.user, item.intake))
    if item.dish_id is not None and not any(dish.id == item.dish_id for dish in dish_options):
        dish_options = [item.dish] + dish_options

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
        except (TypeError, ValueError):
            return JsonResponse({'error': 'Datos inválidos.'}, status=400)

        if payload.get('is_free_meal'):
            item.dish = None
            item.quantity = 0
            item.kcal = Decimal('0')
            item.is_free_meal = True
            item.save(update_fields=['dish', 'quantity', 'kcal', 'is_free_meal'])

            day_kcal = TemplateIntake.objects.filter(template=template, menu_day=item.menu_day).aggregate(
                total=Sum('kcal'),
            )['total'] or Decimal('0')

            return JsonResponse({
                'dish_id': None,
                'dish_name': 'Comida libre',
                'is_free_meal': True,
                'quantity': 0,
                'kcal': 0.0,
                'prot': 0.0,
                'fat': 0.0,
                'carb': 0.0,
                'day_kcal': float(day_kcal),
            })

        try:
            quantity = int(payload.get('quantity'))
        except (TypeError, ValueError):
            quantity = None
        if not quantity or quantity <= 0:
            return JsonResponse({'error': 'Indica una cantidad válida.'}, status=400)

        try:
            dish_id = int(payload.get('dish_id'))
        except (TypeError, ValueError):
            dish_id = None
        dish = next((d for d in dish_options if d.id == dish_id), None)
        if dish is None:
            return JsonResponse({'error': 'Selecciona un plato válido.'}, status=400)

        nutrition = calculate_dish_nutrition(dish)
        totals = _intake_nutrition(nutrition, quantity)

        item.dish = dish
        item.quantity = quantity
        item.kcal = totals['kcal']
        item.is_free_meal = False
        item.save(update_fields=['dish', 'quantity', 'kcal', 'is_free_meal'])

        day_kcal = TemplateIntake.objects.filter(template=template, menu_day=item.menu_day).aggregate(
            total=Sum('kcal'),
        )['total'] or Decimal('0')

        return JsonResponse({
            'dish_id': dish.id,
            'dish_name': dish.name,
            'is_free_meal': False,
            'quantity': quantity,
            'kcal': float(totals['kcal']),
            'prot': float(totals['prot']),
            'fat': float(totals['fat']),
            'carb': float(totals['carb']),
            'day_kcal': float(day_kcal),
        })

    return JsonResponse({
        'dish_id': item.dish_id,
        'quantity': item.quantity,
        'is_free_meal': item.is_free_meal,
        'options': [{'id': dish.id, 'name': dish.name} for dish in dish_options],
    })


@login_required
@require_http_methods(['GET'])
def copy_template_intake(request, template_id, item_id):
    """Copiar una toma (plato + cantidad + estado de comida libre) de una
    plantilla para pegarla en otras celdas de la misma. Mismo contrato JSON
    que Menus.views.copy_menu_intake."""
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=True), request.user), id=template_id)
    item = get_object_or_404(
        TemplateIntake.objects.select_related('dish', 'intake'), id=item_id, template=template,
    )

    other_items = list(TemplateIntake.objects.filter(template=template).exclude(id=item.id).select_related('intake'))

    if item.is_free_meal or item.dish_id is None:
        return JsonResponse({
            'dish_id': None,
            'dish_name': 'Comida libre',
            'quantity': 0,
            'is_free_meal': True,
            'target_ids': [other.id for other in other_items],
        })

    distinct_intakes = {}
    for other in other_items:
        distinct_intakes.setdefault(other.intake_id, other.intake)

    compatible_intake_ids = {
        intake_id
        for intake_id, intake in distinct_intakes.items()
        if _dish_options_for_intake(request.user, intake).filter(pk=item.dish_id).exists()
    }

    return JsonResponse({
        'dish_id': item.dish_id,
        'dish_name': item.dish.name,
        'quantity': item.quantity,
        'is_free_meal': False,
        'target_ids': [other.id for other in other_items if other.intake_id in compatible_intake_ids],
    })


@login_required
@require_POST
def deactivate_template(request, id):
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=True), request.user), id=id)
    template.active = False
    template.save(update_fields=['active'])
    messages.success(request, 'La plantilla se ha desactivado correctamente.')
    return redirect('list_templates')


@login_required
@require_POST
def deactivate_templates_bulk(request):
    template_ids = request.POST.getlist('selected_templates')
    count = scoped_queryset(Template.objects.filter(active=True), request.user).filter(
        id__in=template_ids,
    ).update(active=False)

    if count:
        messages.success(request, f'{count} plantilla(s) desactivada(s) correctamente.')
    else:
        messages.warning(request, 'No se seleccionaron plantillas válidas para desactivar.')
    return redirect('list_templates')


@login_required
def list_deactivated_templates(request):
    templates = scoped_queryset(Template.objects.filter(active=False), request.user).order_by('name')
    templates = templates.annotate(avg_daily_kcal=AVG_DAILY_KCAL_ANNOTATION)
    return render(
        request,
        'admin/list_deactivated_templates.html',
        {'templates': templates},
    )


@login_required
@require_POST
def reactivate_template(request, id):
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=False), request.user), id=id)
    template.active = True
    template.save(update_fields=['active'])
    messages.success(request, 'La plantilla se ha reactivado correctamente.')
    return redirect('list_deactivated_templates')


@login_required
@require_POST
def reactivate_templates_bulk(request):
    template_ids = request.POST.getlist('selected_templates')
    count = scoped_queryset(Template.objects.filter(active=False), request.user).filter(
        id__in=template_ids,
    ).update(active=True)
    if count:
        messages.success(request, f'{count} plantilla(s) reactivada(s) correctamente.')
    else:
        messages.warning(request, 'No se seleccionaron plantillas válidas para reactivar.')
    return redirect('list_deactivated_templates')


@login_required
@require_POST
def delete_template(request, id):
    template = get_object_or_404(scoped_queryset(Template.objects.filter(active=False), request.user), id=id)
    template.delete()
    messages.success(request, 'La plantilla se ha eliminado definitivamente.')
    return redirect('list_deactivated_templates')


@login_required
@require_POST
def delete_templates_bulk(request):
    template_ids = request.POST.getlist('selected_templates')
    queryset = scoped_queryset(Template.objects.filter(active=False), request.user).filter(
        id__in=template_ids,
    )
    count = queryset.count()
    queryset.delete()
    if count:
        messages.success(request, f'{count} plantilla(s) eliminada(s) definitivamente.')
    else:
        messages.warning(request, 'No se seleccionaron plantillas válidas para eliminar.')
    return redirect('list_deactivated_templates')


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
