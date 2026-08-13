import copy
import random

from Menus.generator.fitness import fitness

DEFAULT_POP_SIZE = 24
DEFAULT_N_GENERATIONS = 60
DEFAULT_THRESHOLD = 30.0
DEFAULT_MUTATION_RATE = 0.3

# Peso relativo de cada toma "suelta" en el reparto de kcal del dia (por
# nombre de Intake) y su racion minima/maxima realista en gramos. No hace
# falta que los pesos sumen 1: se normalizan sobre las tomas realmente
# seleccionadas, asi que elegir muchas tomas no dispara el total del dia --
# cada una se lleva una porcion proporcional a lo que de verdad representa
# (un tentempie no deberia pesar lo mismo que el desayuno o la comida).
SINGLE_INTAKE_PROFILES = {
    'Desayuno': {'weight': 3.0, 'bounds': (100, 400)},
    'Media mañana': {'weight': 1.0, 'bounds': (30, 150)},
    'Merienda': {'weight': 1.5, 'bounds': (30, 200)},
    'Recena': {'weight': 1.0, 'bounds': (30, 150)},
    'Otros': {'weight': 1.0, 'bounds': (30, 150)},
}
DEFAULT_SINGLE_PROFILE = {'weight': 1.5, 'bounds': (50, 250)}

# Peso relativo de cada grupo comida/cena en el reparto de kcal del dia, y
# como se reparte ese peso entre sus cursos (entrante/principal/postre).
GROUP_WEIGHTS = {'comida': 5.0, 'cena': 4.0}
DEFAULT_GROUP_WEIGHT = 4.0
GROUP_ROLE_SHARE = {'starter': 0.22, 'main': 0.58, 'dessert': 0.20}
GROUP_ROLE_BOUNDS = {
    'starter': (80, 250),
    'main': (120, 400),
    'dessert': (50, 200),
}


def allocate_quantity(kcal_budget, candidate, bounds, max_portion_grams):
    if candidate.kcal_100g <= 0:
        grams = 100
    else:
        grams = round(kcal_budget / candidate.kcal_100g * 100)

    min_grams, max_grams = bounds
    if max_portion_grams:
        max_grams = min(max_grams, max_portion_grams)
        min_grams = min(min_grams, max_grams)  # el limite explicito del usuario manda

    return max(min_grams, min(grams, max_grams))


def _bounds_for(slot, role):
    if slot.kind == 'single':
        return SINGLE_INTAKE_PROFILES.get(slot.label, DEFAULT_SINGLE_PROFILE)['bounds']
    return GROUP_ROLE_BOUNDS.get(role, (50, 300))


def _slot_weight(slot):
    if slot.kind == 'single':
        return SINGLE_INTAKE_PROFILES.get(slot.label, DEFAULT_SINGLE_PROFILE)['weight']
    return GROUP_WEIGHTS.get(slot.label.lower(), DEFAULT_GROUP_WEIGHT)


def _course_kcal_budgets(meal_slots, target):
    """dict[(slot.key, role)] -> presupuesto de kcal para ese curso, repartiendo
    target.kcal por peso de toma (no a partes iguales) y normalizando sobre las
    tomas realmente seleccionadas."""
    slot_weights = {slot.key: _slot_weight(slot) for slot in meal_slots}
    total_weight = sum(slot_weights.values()) or 1

    budgets = {}
    for slot in meal_slots:
        roles = slot.active_roles()
        if not roles:
            continue
        slot_budget = target.kcal * slot_weights[slot.key] / total_weight
        if slot.kind == 'single':
            budgets[(slot.key, roles[0])] = slot_budget
            continue

        role_shares = {role: GROUP_ROLE_SHARE.get(role, 1.0) for role in roles}
        total_share = sum(role_shares.values()) or 1
        for role in roles:
            budgets[(slot.key, role)] = slot_budget * role_shares[role] / total_share
    return budgets


def _random_day(pools, meal_slots, target, max_portion_grams, rng):
    course_budgets = _course_kcal_budgets(meal_slots, target)
    day = {}
    for slot in meal_slots:
        day[slot.key] = {}
        for role in slot.active_roles():
            candidate = rng.choice(pools[slot.key][role])
            budget = course_budgets.get((slot.key, role), 0)
            qty = allocate_quantity(budget, candidate, _bounds_for(slot, role), max_portion_grams)
            day[slot.key][role] = (candidate, qty)
    return day


def tournament_selection(population, target, rng, k=3):
    """Puerto de tourtnament_w_fitness (nubu_generator - copia/tourtnaments.py):
    muestrea k candidatos al azar y se queda con el de menor fitness, repitiendo
    hasta reunir la mitad+1 de la poblacion."""
    target_size = len(population) // 2 + 1
    selected = []
    attempts = 0
    while len(selected) < target_size and attempts < 200:
        attempts += 1
        contenders = rng.sample(population, min(k, len(population)))
        winner = min(contenders, key=lambda day_menu: fitness(day_menu, target))
        selected.append(copy.deepcopy(winner))
    return selected


def mutate(day_menu, pools, meal_slots, target, max_portion_grams, rng):
    """Puerto de mutation_from_DB (nubu_generator - copia/mutations.py):
    reemplaza un unico curso (slot+rol) por otro candidato distinto del pool."""
    day_menu = copy.deepcopy(day_menu)
    slot = rng.choice(meal_slots)
    roles = slot.active_roles()
    if not roles:
        return day_menu

    role = rng.choice(roles)
    pool = pools[slot.key][role]
    current_candidate, _ = day_menu[slot.key][role]

    alternatives = [c for c in pool if c.dish_id != current_candidate.dish_id]
    candidate = rng.choice(alternatives) if alternatives else current_candidate

    budget = _course_kcal_budgets(meal_slots, target).get((slot.key, role), 0)
    qty = allocate_quantity(budget, candidate, _bounds_for(slot, role), max_portion_grams)
    day_menu[slot.key][role] = (candidate, qty)
    return day_menu


def crossover(day_a, day_b, rng):
    """Puerto de crossover (nubu_generator - copia/crossovers.py): intercambia
    el contenido completo de 1 o 2 slots aleatorios entre dos dias padres."""
    day_a = copy.deepcopy(day_a)
    day_b = copy.deepcopy(day_b)

    keys = list(day_a.keys())
    if not keys:
        return day_a, day_b

    n_swap = rng.choice([1, 2]) if len(keys) > 1 else 1
    swap_keys = rng.sample(keys, min(n_swap, len(keys)))
    for key in swap_keys:
        day_a[key], day_b[key] = day_b[key], day_a[key]

    return day_a, day_b


def generate_day(pools, meal_slots, target, max_portion_grams=None,
                  pop_size=DEFAULT_POP_SIZE, n_generations=DEFAULT_N_GENERATIONS,
                  threshold=DEFAULT_THRESHOLD, mutation_rate=DEFAULT_MUTATION_RATE, rng=None):
    rng = rng or random.Random()

    population = [_random_day(pools, meal_slots, target, max_portion_grams, rng) for _ in range(pop_size)]
    best_day = min(population, key=lambda day_menu: fitness(day_menu, target))
    best_score = fitness(best_day, target)
    best_history = [best_score]

    for _ in range(n_generations):
        next_gen = tournament_selection(population, target, rng)

        while len(next_gen) < pop_size:
            if len(next_gen) >= 2:
                child_a, child_b = crossover(next_gen[0], next_gen[1], rng)
                next_gen.append(child_a)
                if len(next_gen) < pop_size:
                    next_gen.append(child_b)
            else:
                next_gen.append(copy.deepcopy(next_gen[0]))
        next_gen = next_gen[:pop_size]

        for i in range(len(next_gen)):
            if rng.random() < mutation_rate:
                next_gen[i] = mutate(next_gen[i], pools, meal_slots, target, max_portion_grams, rng)

        # Elitismo: el mejor individuo encontrado en todo el proceso nunca se
        # pierde entre generaciones (antes se devolvia el mejor de la ULTIMA
        # generacion, que podia ser peor que uno ya encontrado antes).
        next_gen[0] = copy.deepcopy(best_day)

        population = next_gen
        gen_best_score, gen_best_day = min(
            ((fitness(day_menu, target), day_menu) for day_menu in population),
            key=lambda scored: scored[0],
        )
        if gen_best_score < best_score:
            best_score, best_day = gen_best_score, gen_best_day

        best_history.append(best_score)
        if best_score < threshold:
            break

    return best_day, best_history
