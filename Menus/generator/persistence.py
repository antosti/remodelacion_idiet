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


def persist_menu_from_template(user, client, template, start_date):
    """Crea una dieta (Menu) copiando directamente las tomas de una plantilla
    (Template/TemplateIntake) ya completa, sin pasar por el algoritmo
    genetico: una plantilla es un esqueleto de menu ya resuelto por el
    nutricionista, solo hay que trasladarla al rango de fechas del cliente."""
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

        rows = [
            MenuIntake(
                menu=menu,
                dish_id=item.dish_id,
                intake_id=item.intake_id,
                quantity=item.quantity,
                kcal=item.kcal,
                menu_day=item.menu_day,
                intake_alias=item.intake_alias,
                is_free_meal=item.is_free_meal,
            )
            for item in items
        ]
        MenuIntake.objects.bulk_create(rows)

    return menu
