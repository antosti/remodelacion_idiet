import json
import logging
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods

from Dishes.models import Dish, DishCategorySize
from Dishes.views import calculate_dish_nutrition
from FoodGroup.models import FoodGroupExcluded
from idiet.permissions import get_visible_client_or_404, scoped_queryset
from Intakes.models import Intake
from Menus.generator.domain import DietConfig, MealSlotConfig, ROLE_LABELS, deserialize_config
from Menus.generator.meal_structure import get_meal_structure
from Menus.generator.persistence import persist_generated_diet
from Menus.generator.pools import ROLE_TO_DISH_TYPES, _to_candidate
from Menus.generator.service import GenerationError, generate_diet
from Menus.generator.targets import attach_micro_ranges, default_target_for_client, macro_split_for_kcal
from Menus.models import Menu, MenuIntake
from Products.models import ProductExcluded

logger = logging.getLogger('idiet.menus')


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_diet_config_from_post(post, client, standalone, groups):
    days = _parse_int(post.get('days'))
    if not days or days < 1:
        raise ValueError('Indica una duración en días válida (mayor que 0).')

    try:
        start_date = date.fromisoformat(post.get('start_date', ''))
    except ValueError:
        raise ValueError('Indica una fecha de inicio válida.')

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

    if not meal_slots:
        raise ValueError('Selecciona al menos una toma para la dieta.')

    advanced_kcal = _parse_float(post.get('target_kcal'))
    advanced_prot = _parse_float(post.get('target_prot_g'))
    advanced_fat = _parse_float(post.get('target_fat_g'))
    advanced_carb = _parse_float(post.get('target_carb_g'))

    # Cada campo avanzado es independiente: si el nutricionista solo rellena
    # kcal, los macros se derivan de ese valor (no del calculo automatico del
    # cliente, que podia ser muy distinto e ignoraba silenciosamente el kcal
    # tecleado si faltaba cualquiera de los otros tres campos).
    target = macro_split_for_kcal(advanced_kcal) if advanced_kcal is not None else default_target_for_client(client)
    if advanced_prot is not None:
        target.prot_g = advanced_prot
    if advanced_fat is not None:
        target.fat_g = advanced_fat
    if advanced_carb is not None:
        target.carb_g = advanced_carb
    attach_micro_ranges(target, client)

    portion_size = None
    if post.get('limit_portion') == 'on':
        portion_size = post.get('portion_size') or None
        if portion_size not in DishCategorySize.Size.values:
            raise ValueError('Selecciona un tamaño de ración válido.')

    return DietConfig(
        days=days, start_date=start_date, meal_slots=meal_slots,
        target=target, portion_size=portion_size,
    )


@login_required
def create_diet(request, id):
    client = get_visible_client_or_404(request.user, id=id)
    standalone, groups = get_meal_structure()

    if request.method == 'POST':
        try:
            config = build_diet_config_from_post(request.POST, client, standalone, groups)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, 'admin/create_diet_wizard.html', {
                'client': client, 'standalone': standalone, 'groups': groups,
            })

        try:
            days = generate_diet(client, request.user, config)
            persist_generated_diet(request.user, client, config, days)
        except GenerationError as exc:
            messages.error(request, str(exc))
            return render(request, 'admin/create_diet_wizard.html', {
                'client': client, 'standalone': standalone, 'groups': groups,
            })
        except Exception:
            logger.exception('Error generando dieta para cliente %s', client.id)
            messages.error(request, 'Error inesperado al generar la dieta. Inténtelo de nuevo.')
            return render(request, 'admin/create_diet_wizard.html', {
                'client': client, 'standalone': standalone, 'groups': groups,
            })

        messages.success(request, 'Dieta generada correctamente.')
        return redirect('client_detail', id=client.id)

    return render(request, 'admin/create_diet_wizard.html', {
        'client': client,
        'standalone': standalone,
        'groups': groups,
    })


@login_required
@require_http_methods(['POST'])
def delete_menu(request, client_id, menu_id):
    client = get_visible_client_or_404(request.user, id=client_id)
    menu = get_object_or_404(Menu, id=menu_id, client=client)
    menu.delete()
    messages.success(request, 'Dieta eliminada correctamente.')
    return redirect('client_diets', id=client.id)


@login_required
def client_diets(request, id):
    client = get_visible_client_or_404(request.user, id=id)
    menus = client.menus.annotate(dishes_count=Count('menuintake')).order_by('-date_ini')
    for menu in menus:
        menu.days_count = (menu.date_fin - menu.date_ini).days + 1
    return render(request, 'admin/client_diets.html', {'client': client, 'menus': menus})


def _intake_nutrition(nutrition, quantity):
    """kcal/prot/fat/carb (Decimal) para `quantity` gramos, a partir del
    `nutrition` por 100g de calculate_dish_nutrition."""
    factor = Decimal(quantity) / Decimal('100')
    return {
        'kcal': Decimal(str(nutrition['kcal_100g'])) * factor,
        'prot': round(Decimal(str(nutrition['protein_100g'])) * factor, 1),
        'fat': round(Decimal(str(nutrition['fat_100g'])) * factor, 1),
        'carb': round(Decimal(str(nutrition['carbs_100g'])) * factor, 1),
    }


def _dish_options_for_intake(client, user, intake):
    """Platos candidatos para reasignar una toma ya generada: mismo rol
    (entrante/principal/postre/unico) e ingesta que usa el generador
    automatico (ver Menus.generator.pools), respetando propiedad y las
    exclusiones del cliente."""
    dish_types = ROLE_TO_DISH_TYPES.get(intake.course_role, [Dish.DishType.MAIN, Dish.DishType.SINGLE])
    qs = Dish.objects.filter(active=True, dish_type__in=dish_types)
    qs = qs.filter(Q(intakes__isnull=True) | Q(intakes=intake)).distinct()
    qs = scoped_queryset(qs, user, include_unassigned=True)

    excluded_products = set(ProductExcluded.objects.filter(client=client).values_list('product_id', flat=True))
    excluded_groups = set(FoodGroupExcluded.objects.filter(client=client).values_list('food_group_id', flat=True))
    if excluded_products:
        qs = qs.exclude(product__id__in=excluded_products)
    if excluded_groups:
        qs = qs.exclude(product__food_group_id__in=excluded_groups)

    return qs.order_by('name')


def _infer_meal_slots_from_menu(menu):
    """Reconstruye las tomas (MealSlotConfig) de una dieta ya generada a
    partir de las Intake realmente usadas en sus MenuIntake, para poder
    rehacer dietas generadas antes de que existiera Menu.generation_config."""
    intake_ids = MenuIntake.objects.filter(menu=menu).values_list('intake_id', flat=True).distinct()
    intakes = list(Intake.objects.filter(id__in=intake_ids))

    meal_slots = [
        MealSlotConfig(key=f'single-{intake.id}', label=intake.name, kind='single', intakes={'single': intake})
        for intake in intakes if intake.course_role == Intake.CourseRole.SINGLE
    ]

    groups = {}
    for intake in intakes:
        if intake.meal_group:
            groups.setdefault(intake.meal_group, {})[intake.course_role] = intake
    for group_key, group_intakes in groups.items():
        meal_slots.append(MealSlotConfig(
            key=f'group-{group_key}', label=group_key.capitalize(), kind='group',
            intakes=group_intakes,
            include_starter='starter' in group_intakes,
            include_dessert='dessert' in group_intakes,
        ))
    return meal_slots


def _infer_target_from_menu(menu, client):
    """Objetivo nutricional para rehacer un menu sin generation_config
    guardado: la media de kcal/dia de la propia dieta actual, para mantener
    el objetivo con el que de verdad se genero en vez de recalcular el valor
    por defecto del cliente (que puede ser muy distinto, ej. si el
    nutricionista tecleo un kcal/dia manual al crearla)."""
    day_totals = MenuIntake.objects.filter(menu=menu).values('menu_day').annotate(total=Sum('kcal'))
    if not day_totals:
        return attach_micro_ranges(default_target_for_client(client), client)
    avg_kcal = sum(float(row['total']) for row in day_totals) / len(day_totals)
    return attach_micro_ranges(macro_split_for_kcal(avg_kcal), client)


def _config_for_regenerate(menu, client):
    """DietConfig para rehacer `menu`: usa la configuracion guardada si existe
    (Menu.generation_config); si no (dietas generadas antes de esa funcion),
    la reconstruye a partir de las tomas realmente usadas y de las kcal/dia
    medias de la dieta actual. None si no hay tomas de las que partir."""
    days = (menu.date_fin - menu.date_ini).days + 1
    if menu.generation_config:
        return deserialize_config(menu.generation_config, days=days, start_date=menu.date_ini)

    meal_slots = _infer_meal_slots_from_menu(menu)
    if not meal_slots:
        return None
    return DietConfig(
        days=days, start_date=menu.date_ini, meal_slots=meal_slots,
        target=_infer_target_from_menu(menu, client),
    )


WEEKDAY_NAMES_ES = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

# Orden de filas del calendario, coincide con los intake_alias que genera
# Menus.generator.persistence.persist_generated_diet (ROLE_LABELS + label de
# grupo 'Comida'/'Cena'), en el mismo orden que las Intake sembradas.
CANONICAL_ALIAS_ORDER = [
    'Desayuno', 'Media mañana',
    'Entrante - Comida', 'Plato principal - Comida', 'Postre - Comida',
    'Merienda',
    'Entrante - Cena', 'Plato principal - Cena', 'Postre - Cena',
    'Recena', 'Otros',
]


@login_required
def diet_detail(request, client_id, menu_id):
    client = get_visible_client_or_404(request.user, id=client_id)
    menu = get_object_or_404(Menu, id=menu_id, client=client)

    intakes = list(MenuIntake.objects.filter(menu=menu).select_related('dish'))

    nutrition_cache = {}

    def nutrition_for(dish):
        if dish.id not in nutrition_cache:
            nutrition_cache[dish.id] = calculate_dish_nutrition(dish)
        return nutrition_cache[dish.id]

    cells = {}
    day_totals = {}
    for item in intakes:
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

    weeks = []
    if intakes:
        first_monday = menu.date_ini - timedelta(days=menu.date_ini.weekday())
        current = first_monday
        while current <= menu.date_fin:
            days_info = []
            for offset in range(7):
                d = current + timedelta(days=offset)
                in_range = menu.date_ini <= d <= menu.date_fin
                day_index = (d - menu.date_ini).days if in_range else None
                days_info.append({
                    'date': d,
                    'weekday_name': WEEKDAY_NAMES_ES[offset],
                    'in_range': in_range,
                    'day_index': day_index,
                    'totals': day_totals.get(day_index),
                })

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
            current += timedelta(days=7)

    return render(request, 'admin/diet_detail.html', {
        'client': client, 'menu': menu, 'weeks': weeks,
        'can_regenerate': bool(weeks),
    })


@login_required
@require_http_methods(['GET', 'POST'])
def edit_menu_intake(request, client_id, menu_id, item_id):
    """Editar una unica toma (plato + cantidad) de una dieta ya generada, sin
    tocar el resto del menu. GET devuelve el estado actual y los platos
    candidatos para esa ingesta; POST aplica el cambio."""
    client = get_visible_client_or_404(request.user, id=client_id)
    menu = get_object_or_404(Menu, id=menu_id, client=client)
    item = get_object_or_404(MenuIntake.objects.select_related('dish', 'intake'), id=item_id, menu=menu)

    dish_options = list(_dish_options_for_intake(client, request.user, item.intake))
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

            day_kcal = MenuIntake.objects.filter(menu=menu, menu_day=item.menu_day).aggregate(
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

        day_kcal = MenuIntake.objects.filter(menu=menu, menu_day=item.menu_day).aggregate(
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
@require_http_methods(['POST'])
def regenerate_menu(request, client_id, menu_id):
    """Borra la dieta actual y lanza de nuevo el proceso de generacion con la
    misma configuracion (Menu.generation_config), manteniendo en su sitio los
    platos marcados como bloqueados (`locked_items`, ids de MenuIntake)."""
    client = get_visible_client_or_404(request.user, id=client_id)
    menu = get_object_or_404(Menu, id=menu_id, client=client)

    try:
        config = _config_for_regenerate(menu, client)
    except Exception:
        logger.exception('Error reconstruyendo configuración de dieta %s', menu.id)
        messages.error(request, 'No se ha podido leer la configuración original de esta dieta.')
        return redirect('diet_detail', client_id=client.id, menu_id=menu.id)

    if config is None:
        messages.error(request, 'Esta dieta no tiene platos y no se puede rehacer.')
        return redirect('diet_detail', client_id=client.id, menu_id=menu.id)

    locked_ids = [item_id for item_id in (_parse_int(v) for v in request.POST.getlist('locked_items')) if item_id]
    locked_items = list(
        MenuIntake.objects.filter(id__in=locked_ids, menu=menu).select_related('dish')
    )

    alias_to_slot_role = {}
    for slot in config.meal_slots:
        for role in slot.active_roles():
            alias = slot.label if slot.kind == 'single' else f'{ROLE_LABELS[role]} - {slot.label}'
            alias_to_slot_role[alias] = (slot.key, role)

    try:
        days = generate_diet(client, request.user, config)
    except GenerationError as exc:
        messages.error(request, str(exc))
        return redirect('diet_detail', client_id=client.id, menu_id=menu.id)
    except Exception:
        logger.exception('Error rehaciendo dieta %s', menu.id)
        messages.error(request, 'Error inesperado al rehacer la dieta. Inténtelo de nuevo.')
        return redirect('diet_detail', client_id=client.id, menu_id=menu.id)

    for item in locked_items:
        if item.dish_id is None:
            # Toma libre (sin plato): no hay DishCandidate equivalente, no se
            # puede bloquear/mantener al rehacer. Se regenera como una toma normal.
            continue
        slot_role = alias_to_slot_role.get(item.intake_alias)
        if not slot_role:
            continue
        slot_key, role = slot_role
        if item.menu_day >= len(days) or role not in days[item.menu_day].get(slot_key, {}):
            continue
        candidate = _to_candidate(item.dish, None)
        days[item.menu_day][slot_key][role] = (candidate, item.quantity)

    with transaction.atomic():
        menu.delete()
        new_menu = persist_generated_diet(request.user, client, config, days)

    messages.success(request, 'Dieta rehecha correctamente.')
    return redirect('diet_detail', client_id=client.id, menu_id=new_menu.id)
