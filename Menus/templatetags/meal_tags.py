from django import template

register = template.Library()


@register.simple_tag
def meal_options(standalone, groups):
    """Tomas sencillas y grupos (comida/cena) de get_meal_structure en una
    sola lista en orden cronologico (Intake.order; un grupo usa el menor
    order de sus tomas), para el paso 2 de los wizards de dieta y plantilla.
    Cada elemento: {'kind': 'single', 'intake'} o {'kind': 'group', 'key', 'group'}."""
    options = [{'kind': 'single', 'intake': intake, 'order': intake.order} for intake in standalone]
    for key, group in groups.items():
        orders = [intake.order for intake in group.values() if intake is not None and intake.meal_group == key]
        if not orders:
            orders = [intake.order for intake in group.values() if intake is not None]
        options.append({'kind': 'group', 'key': key, 'group': group, 'order': min(orders)})
    return sorted(options, key=lambda option: option['order'])
