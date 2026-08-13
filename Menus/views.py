import logging
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, render, redirect

from Dishes.views import calculate_dish_nutrition
from idiet.permissions import get_visible_client_or_404
from Menus.generator.domain import DietConfig, MealSlotConfig, NutritionTarget
from Menus.generator.meal_structure import get_meal_structure
from Menus.generator.persistence import persist_generated_diet
from Menus.generator.service import GenerationError, generate_diet
from Menus.generator.targets import default_target_for_client
from Menus.models import Menu, MenuIntake

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

    advanced_values = [
        _parse_float(post.get('target_kcal')),
        _parse_float(post.get('target_prot_g')),
        _parse_float(post.get('target_fat_g')),
        _parse_float(post.get('target_carb_g')),
    ]

    if all(value is not None for value in advanced_values):
        target = NutritionTarget(
            kcal=advanced_values[0], prot_g=advanced_values[1],
            fat_g=advanced_values[2], carb_g=advanced_values[3],
        )
    else:
        target = default_target_for_client(client)

    max_portion_grams = None
    if post.get('limit_portion') == 'on':
        max_portion_grams = _parse_int(post.get('max_portion_grams'))

    return DietConfig(
        days=days, start_date=start_date, meal_slots=meal_slots,
        target=target, max_portion_grams=max_portion_grams,
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
def client_diets(request, id):
    client = get_visible_client_or_404(request.user, id=id)
    menus = client.menus.annotate(dishes_count=Count('menuintake')).order_by('-date_ini')
    for menu in menus:
        menu.days_count = (menu.date_fin - menu.date_ini).days + 1
    return render(request, 'admin/client_diets.html', {'client': client, 'menus': menus})


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
        nutrition = nutrition_for(item.dish)
        factor = Decimal(item.quantity) / Decimal('100')
        item.prot_total = round(Decimal(str(nutrition['protein_100g'])) * factor, 1)
        item.fat_total = round(Decimal(str(nutrition['fat_100g'])) * factor, 1)
        item.carb_total = round(Decimal(str(nutrition['carbs_100g'])) * factor, 1)

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
                    'cells': [cells.get((day['day_index'], alias)) for day in days_info],
                }
                for alias in row_aliases
            ]

            weeks.append({'days': days_info, 'rows': week_rows})
            current += timedelta(days=7)

    return render(request, 'admin/diet_detail.html', {
        'client': client, 'menu': menu, 'weeks': weeks,
    })
