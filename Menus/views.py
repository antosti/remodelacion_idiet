import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from idiet.permissions import get_visible_client_or_404
from Menus.generator.domain import DietConfig, MealSlotConfig, NutritionTarget
from Menus.generator.meal_structure import get_meal_structure
from Menus.generator.persistence import persist_generated_diet
from Menus.generator.service import GenerationError, generate_diet
from Menus.generator.targets import default_target_for_client

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
            days = generate_diet(client, config)
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
