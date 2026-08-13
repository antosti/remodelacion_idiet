import copy
import random

from Menus.generator.fitness import fitness

DEFAULT_POP_SIZE = 24
DEFAULT_N_GENERATIONS = 60
DEFAULT_THRESHOLD = 30.0


def allocate_quantity(kcal_budget, candidate, max_portion_grams):
    if candidate.kcal_100g <= 0:
        grams = 100
    else:
        grams = round(kcal_budget / candidate.kcal_100g * 100)

    grams = max(20, grams)
    if max_portion_grams:
        grams = min(grams, max_portion_grams)
    return grams


def _kcal_per_course(meal_slots, target):
    total_courses = sum(len(slot.active_roles()) for slot in meal_slots)
    return (target.kcal / total_courses) if total_courses else 0


def _random_day(pools, meal_slots, target, max_portion_grams, rng):
    kcal_per_course = _kcal_per_course(meal_slots, target)
    day = {}
    for slot in meal_slots:
        day[slot.key] = {}
        for role in slot.active_roles():
            candidate = rng.choice(pools[slot.key][role])
            qty = allocate_quantity(kcal_per_course, candidate, max_portion_grams)
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

    kcal_per_course = _kcal_per_course(meal_slots, target)
    qty = allocate_quantity(kcal_per_course, candidate, max_portion_grams)
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
                  threshold=DEFAULT_THRESHOLD, rng=None):
    rng = rng or random.Random()

    population = [_random_day(pools, meal_slots, target, max_portion_grams, rng) for _ in range(pop_size)]
    best_day = min(population, key=lambda day_menu: fitness(day_menu, target))
    best_history = []

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

        if rng.random() < 0.5:
            idx = rng.randrange(pop_size)
            next_gen[idx] = mutate(next_gen[idx], pools, meal_slots, target, max_portion_grams, rng)

        population = next_gen
        best_score, best_day = min(
            ((fitness(day_menu, target), day_menu) for day_menu in population),
            key=lambda scored: scored[0],
        )
        best_history.append(best_score)
        if best_score < threshold:
            break

    return best_day, best_history
