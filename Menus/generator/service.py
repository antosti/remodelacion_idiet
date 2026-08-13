from Menus.generator.domain import ROLE_LABELS
from Menus.generator.ga import generate_day
from Menus.generator.pools import build_candidate_pools


class GenerationError(Exception):
    """Error esperado (config invalida / sin platos suficientes), se muestra tal cual al usuario."""


def generate_diet(client, config, rng=None):
    if not config.meal_slots:
        raise GenerationError('Selecciona al menos una toma para generar la dieta.')

    pools = build_candidate_pools(client, config.meal_slots)

    for slot in config.meal_slots:
        for role in slot.active_roles():
            if not pools[slot.key].get(role):
                raise GenerationError(
                    f'No hay platos de tipo «{ROLE_LABELS[role]}» activos y compatibles '
                    f'con este cliente para «{slot.label}».'
                )

    days = []
    for _ in range(config.days):
        day_menu, _history = generate_day(
            pools, config.meal_slots, config.target, config.max_portion_grams, rng=rng,
        )
        days.append(day_menu)

    return days
