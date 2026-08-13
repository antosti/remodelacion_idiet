from datetime import date

from Menus.generator.domain import NutritionTarget

# Factores de actividad por sexo/nivel, identicos a los usados en el algoritmo
# legacy (nubu_generator - copia/user_calculation.py) y alineados con
# Clients.models.Client.ACTIVITY_LEVELS_CHOICES.
ACTIVITY_FACTORS = {
    'Male': {'Reposo': 1.00, 'Ligera': 1.55, 'Moderada': 1.78, 'Intensa': 2.10},
    'Female': {'Reposo': 1.00, 'Ligera': 1.30, 'Moderada': 1.64, 'Intensa': 1.82},
}


def compute_age(birth_date, on=None):
    on = on or date.today()
    years = on.year - birth_date.year
    if (on.month, on.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def harris_benedict_bmr(weight_kg, height_cm, age_years, gender):
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age_years
    return base + 5 if gender == 'Male' else base - 161


def default_target_for_client(client):
    """Objetivo nutricional por defecto para un cliente, usado cuando el
    nutricionista no rellena la configuracion avanzada del wizard."""
    if client.gasto_energetico:
        kcal = float(client.gasto_energetico)
    else:
        age = compute_age(client.birth_date)
        bmr = harris_benedict_bmr(float(client.weight), client.height, age, client.gender)
        factor = ACTIVITY_FACTORS.get(client.gender, ACTIVITY_FACTORS['Male']).get(client.activity_level, 1.55)
        kcal = bmr * factor

    prot_g = kcal * 0.20 / 4
    fat_g = kcal * 0.25 / 9
    carb_g = kcal * 0.55 / 4

    return NutritionTarget(
        kcal=round(kcal),
        prot_g=round(prot_g),
        fat_g=round(fat_g),
        carb_g=round(carb_g),
    )
