from Intakes.models import Intake


def get_meal_structure():
    """Devuelve (standalone, groups):
    - standalone: lista de Intake de toma unica (desayuno, merienda...).
    - groups: dict {'comida': {'starter': Intake|None, 'main': Intake, 'dessert': Intake|None}, 'cena': {...}}
    """
    intakes = list(Intake.objects.filter(status=True).order_by('order'))

    standalone = [i for i in intakes if i.course_role == Intake.CourseRole.SINGLE]

    groups = {}
    for intake in intakes:
        if intake.meal_group:
            groups.setdefault(intake.meal_group, {})[intake.course_role] = intake

    dessert = next((i for i in intakes if i.course_role == Intake.CourseRole.DESSERT), None)
    for group in groups.values():
        group.setdefault(Intake.CourseRole.DESSERT, dessert)

    return standalone, groups
