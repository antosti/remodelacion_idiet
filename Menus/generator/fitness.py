from Menus.generator.domain import day_totals


def _sq_rel_error(value, optimal):
    """Error cuadratico relativo: penaliza mas cuanto mas se aleja `value` de `optimal`,
    normalizado por `optimal` para que kcal y gramos sean comparables entre si."""
    if optimal <= 0:
        return 0.0
    return (1 / optimal) * (value - optimal) ** 2


def fitness(day_menu, target):
    """Puerto de total_f_fitness (nubu_generator - copia/fitness_functions.py),
    version sin micronutrientes. Cuanto mas bajo, mejor se ajusta el dia a los
    objetivos nutricionales del cliente."""
    kcal, prot, fat, carb = day_totals(day_menu)
    return (
        _sq_rel_error(kcal, target.kcal)
        + _sq_rel_error(carb, target.carb_g)
        + 10 * _sq_rel_error(fat, target.fat_g)
        + 15 * _sq_rel_error(prot, target.prot_g)
    )
