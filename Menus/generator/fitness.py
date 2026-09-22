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
    intervalo, no un punto. Solo se usa para decidir si un dia es aceptable
    (within_micro_ranges), no para guiar al GA (ver _micro_center_penalty)."""
    if lo is not None and value < lo:
        return ((lo - value) / lo) ** 2
    if hi is not None and value > hi:
        return ((value - hi) / hi) ** 2
    return 0.0


# Para rangos abiertos por un lado (fibra: solo minimo; colesterol/sodio:
# solo maximo), tirar exactamente del unico extremo definido empuja el valor
# justo al borde -- con la variabilidad propia del GA eso lo cruza la mitad
# de las veces (probado: colesterol paso de 55% a 100% fuera de rango al
# tirar exactamente de su maximo, 100mg). En vez de eso se apunta a un
# margen de seguridad dentro del lado bueno del rango: 20% por encima del
# minimo, o 20% por debajo del maximo.
OPEN_RANGE_SAFETY_MARGIN = 0.2


def _micro_target(lo, hi):
    """Valor de referencia de un micronutriente: el punto medio de [lo, hi]
    si ambos extremos existen (puerto de total_f_fitness_micros en
    nubu_generator/fitness_functions.py, que siempre compara contra un unico
    optimal -- ahi el punto medio -- en vez de contra un intervalo), o un
    margen de seguridad dentro del unico extremo definido si el rango es
    abierto por el otro lado (ver OPEN_RANGE_SAFETY_MARGIN)."""
    if lo is None:
        return hi * (1 - OPEN_RANGE_SAFETY_MARGIN)
    if hi is None:
        return lo * (1 + OPEN_RANGE_SAFETY_MARGIN)
    return (lo + hi) / 2


def _micro_center_penalty(day_menu, micro_ranges):
    totals = day_micro_totals(day_menu)
    return sum(
        _sq_rel_error(totals.get(micro_id, 0.0), _micro_target(lo, hi))
        for micro_id, (lo, hi) in micro_ranges.items()
    )


def _micro_boundary_penalty(day_menu, micro_ranges):
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
    return _micro_boundary_penalty(day_menu, micro_ranges) == 0.0


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
        score += MICRO_PENALTY_WEIGHT * _micro_center_penalty(day_menu, target.micro_ranges)
    return score
