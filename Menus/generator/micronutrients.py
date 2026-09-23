from Menus.generator.targets import compute_age

# ids de Micronutrients.models.Micronutrient (ver Micronutrients/migrations/0002_seed_micronutrients.py)
MICRO_IDS = {
    'fibra': 2,
    'colesterol': 7,
    'vit_c': 18,
    'vit_d': 19,
    'vit_e': 21,
    'sodio': 24,
    'potasio': 25,
    'calcio': 27,
    'hierro': 29,
    'cromo': 34,
    'yodo': 37,
}


def ranges_for_client(client):
    """dict[micronutrient_id] -> (minimo, maximo), alguno de los dos puede ser
    None. Puerto de calcium_levels/fiber_levels/.../sodium_levels
    (nubu_generator - copia/user_calculation.py:459-674), usando solo edad y
    sexo: los flags de patologia/preferencia del motor legado (potenciar_*,
    cholesterol, hypertension...) no existen en Clients.models.Client, se
    asumen todos desactivados."""
    age = compute_age(client.birth_date)
    sex = 'male' if (client.gender or '').lower() == 'male' else 'female'
    r = {}

    if 4 <= age <= 9:
        r[MICRO_IDS['calcio']] = (800, 800)
    elif 10 <= age <= 19:
        r[MICRO_IDS['calcio']] = (1000, 1300)
    elif age >= 20:
        r[MICRO_IDS['calcio']] = (1000, 2500)

    if 1 <= age <= 3:
        fiber = 19
    elif 4 <= age <= 8:
        fiber = 25
    elif 9 <= age <= 13:
        fiber = 31 if sex == 'male' else 26
    elif 14 <= age <= 18:
        fiber = 38 if sex == 'male' else 26
    elif 19 <= age <= 50:
        fiber = 38 if sex == 'male' else 25
    else:
        fiber = 30 if sex == 'male' else 21
    r[MICRO_IDS['fibra']] = (fiber, None)

    if 4 <= age <= 9:
        r[MICRO_IDS['hierro']] = (9, 10)
    elif 10 <= age <= 19:
        r[MICRO_IDS['hierro']] = (12, 30) if sex == 'male' else (15, 30)
    elif 20 <= age <= 49:
        r[MICRO_IDS['hierro']] = (10, 30) if sex == 'male' else (18, 40)
    elif age >= 50:
        r[MICRO_IDS['hierro']] = (10, 30)

    if 4 <= age <= 5:
        r[MICRO_IDS['potasio']] = (1100, 1100)
    elif 6 <= age <= 9:
        r[MICRO_IDS['potasio']] = (2000, 2000)
    elif 10 <= age <= 13:
        r[MICRO_IDS['potasio']] = (3100, 3100)
    elif 14 <= age <= 19:
        r[MICRO_IDS['potasio']] = (3100, 3500)
    elif age >= 20:
        r[MICRO_IDS['potasio']] = (3500, 3500)

    if 4 <= age <= 5:
        r[MICRO_IDS['yodo']] = (90, 800)
    elif 6 <= age <= 9:
        r[MICRO_IDS['yodo']] = (120, 800)
    elif 10 <= age <= 13:
        r[MICRO_IDS['yodo']] = (155, 800) if sex == 'male' else (130, 800)
    elif age >= 14:
        r[MICRO_IDS['yodo']] = (150, 1000)

    if 4 <= age <= 9:
        r[MICRO_IDS['vit_c']] = (45, 1800)
    elif 10 <= age <= 13:
        r[MICRO_IDS['vit_c']] = (50, 1800)
    elif 14 <= age <= 59:
        r[MICRO_IDS['vit_c']] = (60, 1800)
    elif age >= 60:
        r[MICRO_IDS['vit_c']] = (70, 1800)

    if 4 <= age <= 9:
        r[MICRO_IDS['vit_e']] = (7, 380)
    elif 10 <= age <= 13:
        r[MICRO_IDS['vit_e']] = (11, 380)
    elif age >= 14:
        r[MICRO_IDS['vit_e']] = (15, 380)

    # vit_d: sin rango. La ingesta adecuada real (~200 UI) es un valor puntual,
    # no un intervalo, y con datos de alimentos reales practicamente nunca cae
    # justo en ese punto -> dejaba el dia "fuera de rango" siempre, sin que
    # eso reflejase un problema real del menu generado.
    r[MICRO_IDS['cromo']] = (30, 200)
    r[MICRO_IDS['colesterol']] = (None, 100)  # asume cholesterol=0 (sin patologia)
    r[MICRO_IDS['sodio']] = (None, 1000)      # asume hypertension=0 (sin patologia)

    return r
