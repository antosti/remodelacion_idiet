from Menus.generator.domain import ROLE_LABELS
from Menus.generator.fitness import fitness, within_micro_ranges
from Menus.generator.ga import generate_day
from Menus.generator.pools import build_candidate_pools

# Si el mejor dia de una tanda del GA se sale de algun target.micro_ranges, se
# vuelve a generar desde cero hasta este numero de intentos; si ninguno entra
# en rango, se usa el de menor fitness de todos los intentos (ver
# _generate_day_within_ranges).
MAX_DAY_ATTEMPTS = 5


class GenerationError(Exception):
    """Error esperado (config invalida / sin platos suficientes), se muestra tal cual al usuario."""


def _generate_day_within_ranges(pools, config, rng):
    best_day, best_score = None, None

    for _attempt in range(MAX_DAY_ATTEMPTS):
        day_menu, _history = generate_day(
            pools, config.meal_slots, config.target, config.max_portion_grams, rng=rng,
        )

        if within_micro_ranges(day_menu, config.target.micro_ranges):
            return day_menu

        score = fitness(day_menu, config.target)
        if best_day is None or score < best_score:
            best_day, best_score = day_menu, score

    return best_day


def generate_diet(client, user, config, rng=None):
    if not config.meal_slots:
        raise GenerationError('Selecciona al menos una toma para generar la dieta.')

    pools = build_candidate_pools(client, user, config.meal_slots, config.portion_size)

    for slot in config.meal_slots:
        for role in slot.active_roles():
            if not pools[slot.key].get(role):
                raise GenerationError(
                    f'No hay platos de tipo «{ROLE_LABELS[role]}» activos y compatibles '
                    f'con este cliente para «{slot.label}».'
                )

    return [_generate_day_within_ranges(pools, config, rng) for _ in range(config.days)]
