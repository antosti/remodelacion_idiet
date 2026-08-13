from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from Menus.generator.domain import ROLE_LABELS
from Menus.models import Menu, MenuIntake


def persist_generated_diet(user, client, config, days):
    end_date = config.start_date + timedelta(days=config.days - 1)

    with transaction.atomic():
        menu = Menu.objects.create(
            user=user,
            client=client,
            date_ini=config.start_date,
            date_fin=end_date,
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
