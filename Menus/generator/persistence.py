from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from Menus.generator.domain import ROLE_LABELS, serialize_config
from Menus.generator.service import GenerationError
from Menus.models import Menu, MenuIntake
from Plantillas.models import TemplateIntake


def persist_generated_diet(user, client, config, days):
    end_date = config.start_date + timedelta(days=config.days - 1)

    with transaction.atomic():
        menu = Menu.objects.create(
            user=user,
            client=client,
            date_ini=config.start_date,
            date_fin=end_date,
            generation_config=serialize_config(config),
        )

        rows = []
        for day_index, day_menu in enumerate(days):
            for slot in config.meal_slots:
                for role, entry in day_menu[slot.key].items():
                    if entry is None:
                        continue

                    candidate, qty = entry
                    intake = slot.intakes[role]
                    kcal = Decimal(str(candidate.kcal_100g)) * qty / Decimal('100')
                    alias = slot.label if slot.kind == 'single' else f'{ROLE_LABELS[role]} - {slot.label}'

                    rows.append(MenuIntake(
                        menu=menu,
                        dish_id=candidate.dish_id,
                        intake=intake,
                        quantity=qty,
                        kcal=kcal,
                        menu_day=day_index,
                        intake_alias=alias,
                    ))

        MenuIntake.objects.bulk_create(rows)

    return menu


def _template_day_factors(items, target_kcal):
    """Factor de escala por menu_day para que cada dia de la plantilla llegue
    a `target_kcal`, aplicado por igual a todos sus platos.

    En los dias con comida libre el objetivo incluye la parte que ocuparia esa
    toma (media de kcal de la misma intake_alias en los dias en que si tiene
    plato), para que el resto de platos no la compense. Si no se puede estimar,
    se usa el factor medio de los dias sin comida libre; si tampoco lo hay, el
    dia no se escala."""
    target = Decimal(str(target_kcal))
    day_kcal = {}
    free_aliases = {}
    alias_kcal = {}
    for item in items:
        if item.is_free_meal or item.dish_id is None:
            free_aliases.setdefault(item.menu_day, []).append(item.intake_alias)
        else:
            day_kcal[item.menu_day] = day_kcal.get(item.menu_day, Decimal('0')) + item.kcal
            alias_kcal.setdefault(item.intake_alias, []).append(item.kcal)

    full_day_factors = [
        target / kcal for day, kcal in day_kcal.items()
        if day not in free_aliases and kcal > 0
    ]
    fallback = sum(full_day_factors) / len(full_day_factors) if full_day_factors else None

    factors = {}
    for day, kcal in day_kcal.items():
        if kcal <= 0:
            continue
        aliases = free_aliases.get(day, [])
        if not aliases:
            factors[day] = target / kcal
            continue
        if all(alias in alias_kcal for alias in aliases):
            free_share = sum(sum(alias_kcal[alias]) / len(alias_kcal[alias]) for alias in aliases)
            factors[day] = target / (kcal + free_share)
        elif fallback is not None:
            factors[day] = fallback
    return factors


def persist_menu_from_template(user, client, template, start_date, target_kcal=None):
    """Crea una dieta (Menu) copiando directamente las tomas de una plantilla
    (Template/TemplateIntake) ya completa, sin pasar por el algoritmo
    genetico: una plantilla es un esqueleto de menu ya resuelto por el
    nutricionista, solo hay que trasladarla al rango de fechas del cliente.

    Con `target_kcal`, las cantidades de cada dia se escalan
    proporcionalmente (mismo factor para todos sus platos) para ajustarlo a
    ese objetivo; ver _template_day_factors."""
    items = list(TemplateIntake.objects.filter(template=template))
    if any(item.dish_id is None and not item.is_free_meal for item in items):
        raise GenerationError(
            'La plantilla tiene tomas sin asignar; complétala antes de usarla para crear una dieta.',
        )

    end_date = start_date + timedelta(days=template.duration - 1)

    with transaction.atomic():
        menu = Menu.objects.create(
            user=user,
            client=client,
            date_ini=start_date,
            date_fin=end_date,
            generation_config=None,
        )

        factors = _template_day_factors(items, target_kcal) if target_kcal is not None else {}

        rows = []
        for item in items:
            quantity, kcal = item.quantity, item.kcal
            factor = factors.get(item.menu_day)
            if factor is not None and not item.is_free_meal and item.dish_id is not None and quantity > 0:
                quantity = int(round(quantity * factor))
                kcal = (item.kcal * quantity / item.quantity).quantize(Decimal('0.01'))
            rows.append(MenuIntake(
                menu=menu,
                dish_id=item.dish_id,
                intake_id=item.intake_id,
                quantity=quantity,
                kcal=kcal,
                menu_day=item.menu_day,
                intake_alias=item.intake_alias,
                is_free_meal=item.is_free_meal,
            ))
        MenuIntake.objects.bulk_create(rows)

    return menu
