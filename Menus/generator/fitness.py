from Menus.generator.domain import day_micro_totals, day_totals

# Peso del termino de micronutrientes en el fitness, mismo orden que el peso
# 15 ya usado para proteina (ver total_f_fitness_micros en
# nubu_generator - copia/fitness_functions.py para el precedente).
MICRO_PENALTY_WEIGHT = 15


def _sq_rel_error(value, optimal):
    """Error cuadratico relativo: penaliza mas cuanto mas se aleja `value` de `optimal`,
    normalizado por `optimal` para que kcal y gramos sean comparables entre si."""
    if optimal <= 0:
        return 0.0
    return (1 / optimal) * (value - optimal) ** 2


def _micro_range_penalty(value, lo, hi):
    """0 si `value` cae dentro de [lo, hi] (alguno puede ser None); si no,
    error cuadratico relativo a la frontera superada. A diferencia de
    _sq_rel_error, no penaliza valores ya dentro de rango: el objetivo es un
    intervalo, no un punto."""
    if lo is not None and value < lo:
        return ((lo - value) / lo) ** 2
    if hi is not None and value > hi:
        return ((value - hi) / hi) ** 2
    return 0.0


def _micro_penalty(day_menu, micro_ranges):
    totals = day_micro_totals(day_menu)
    return sum(
        _micro_range_penalty(totals.get(micro_id, 0.0), lo, hi)
        for micro_id, (lo, hi) in micro_ranges.items()
    )


def within_micro_ranges(day_menu, micro_ranges):
    """True si day_menu no se sale de ningun rango de micro_ranges (o si
    micro_ranges esta vacio, en cuyo caso no hay nada que comprobar). Usado
    por Menus.generator.service para decidir si hace falta regenerar el dia."""
    if not micro_ranges:
        return True
    return _micro_penalty(day_menu, micro_ranges) == 0.0


def fitness(day_menu, target):
    """Puerto de total_f_fitness_micros (nubu_generator - copia/fitness_functions.py).
    Cuanto mas bajo, mejor se ajusta el dia a los objetivos nutricionales del
    cliente. El termino de micronutrientes solo se aplica si target.micro_ranges
    no esta vacio (ver Menus.generator.targets.attach_micro_ranges)."""
    kcal, prot, fat, carb = day_totals(day_menu)
    score = (
        _sq_rel_error(kcal, target.kcal)
        + _sq_rel_error(carb, target.carb_g)
        + 10 * _sq_rel_error(fat, target.fat_g)
        + 15 * _sq_rel_error(prot, target.prot_g)
    )
    if target.micro_ranges:
        score += MICRO_PENALTY_WEIGHT * _micro_penalty(day_menu, target.micro_ranges)
    return score
