"""Reglas de clasificación de Dish -> DishCategory a partir de sus ingredientes y su nombre.

Módulo sin efectos secundarios (sin BaseCommand, sin acceso a BBDD) para poder
importarlo y probarlo de forma aislada desde los comandos de gestión.

Solo se incluyen categorías donde un FoodGroup/SuperGroup identifica una única
DishCategory sin ambigüedad. Categorías que dependen de la preparación (p.ej.
Ensaladas verdes vs. Verduras cocidas) o del corte (Carnes con/sin hueso) no
tienen regla aquí a propósito: el ingrediente por sí solo no las distingue.
"""

import re

# SuperGroup.id -> DishCategory.id
SUPER_GROUP_TO_CATEGORY = {
    1: 8,    # ARROZ -> Arroz
    8: 9,    # PASTA -> Pasta
    9: 10,   # PATATAS -> Patatas
    5: 13,   # HUEVOS -> Tortilla
    7: 7,    # LEGUMBRES -> Cocidos: legumbres, guisos caldosos
    13: 36,  # FRUTOS SECOS -> Frutos secos
}

# FoodGroup.id -> DishCategory.id
FOOD_GROUP_TO_CATEGORY = {
    42: 7,   # Legumbres -> Cocidos: legumbres, guisos caldosos
    44: 13,  # Huevos -> Tortilla
    11: 16,  # Moluscos -> Mariscos y moluscos
    20: 16,  # Crustáceos y otros productos -> Mariscos y moluscos
    15: 17,  # Pescados grasos -> Pescados
    17: 17,  # Pescados con poca grasa -> Pescados
    18: 17,  # Pescados semigrasos -> Pescados
    27: 22,  # Vísceras -> Casquería
    2: 23,   # Frutas -> Fruta fresca
    39: 24,  # Quesos -> Queso
    40: 25,  # Yogur -> Yogurt
    41: 25,  # Yogur y cuajada -> Yogurt
    # 37/38 "Helados y otros lácteos" -> Postres lácteos: descartada. El
    # catálogo mezcla helados/natillas reales con nata de cocina normal
    # (ej. "Nata para montar"), lo que producía falsos positivos en platos
    # salados (verificado con "Crema fría de tomate y espárragos").
    12: 36,  # Frutos secos -> Frutos secos
}


def classify_dish(weighted_grams, min_share, min_mapped_grams):
    """Decide la DishCategory de un plato a partir de sus gramos por categoría candidata.

    weighted_grams: dict[category_id -> gramos] acumulados solo con productos
    cuyo food_group/super_groups resolvió a una única categoría candidata.

    Devuelve (status, category_id o None, leader_share o None).
    status es uno de: 'no_signal', 'weak_signal', 'ambiguous', 'matched'.
    """
    if not weighted_grams:
        return 'no_signal', None, None

    total = sum(weighted_grams.values())
    if total <= 0:
        return 'no_signal', None, None

    leader_id, leader_grams = max(weighted_grams.items(), key=lambda kv: kv[1])
    leader_share = leader_grams / total

    if total < min_mapped_grams:
        return 'weak_signal', None, leader_share
    if leader_share < min_share:
        return 'ambiguous', None, leader_share
    return 'matched', leader_id, leader_share


def pick_size(sizes, total_grams):
    """sizes: lista de (size_id, quantity) de la categoría ya asignada.

    Elige el tramo cuya quantity está más cerca de total_grams; en empate,
    el tramo de menor quantity (convención determinista y documentada).
    """
    if not sizes:
        return None
    return min(sizes, key=lambda s: (abs(s[1] - total_grams), s[1]))[0]


# --- Segundo pase: clasificación por nombre del plato -----------------------
#
# Estas categorías son de preparación/tipo de plato, no de ingrediente: el
# nombre del plato ("pizza", "bocadillo", "sopa"...) es la señal fiable, no
# sus ingredientes (una pizza y una lasaña pueden compartir queso y tomate).
#
# Se excluyen deliberadamente categorías donde el nombre tampoco resuelve la
# ambigüedad de forma fiable:
#   - Fritos (14): "frito"/"a la plancha"/"asado" modifican mayoritariamente
#     platos de carne/pescado (ej. "Pollo a la plancha"), que ya tienen su
#     propia categoría de proteína; forzar "Fritos" por el método de cocción
#     competiría con esa clasificación más específica.
#   - Panes (32): "pan" aparece constantemente como acompañamiento dentro de
#     nombres de otros platos (ej. "Pan integral con aceite y cecina"), no
#     como el plato en sí; no se puede aislar con una palabra clave simple.
#   - Copa (34) y Otros (35): sin patrón de nombre fiable / categoría residual.
#   - Desayunos (1) y Desayuno Ligero (37): la palabra "desayuno" aparece en
#     nombres de platos ya clasificados por ingrediente dominante (fruta,
#     yogur...) y no distingue de forma fiable entre las dos categorías.
#
# Se evalúan en orden: la primera regla que coincide gana (p.ej. "mini pizza"
# debe resolver a Aperitivos antes que la regla genérica de Pizza).
_RAW_NAME_RULES = [
    (2, [r'\bhojaldres?\b', r'\bmontaditos?\b', r'\bcanap[eé]s?\b', r'\bmini\s*pizzas?\b',
         r'\bentrem[eé]ses?\b']),
    (12, [r'\bpizzas?\b']),
    (11, [r'\blasa[ñn]as?\b', r'\blasagn?as?\b', r'\bquiches?\b', r'\bempanadas?\b', r'\bempanadillas?\b']),
    (15, [r'\bbocadillos?\b', r'\bbocatas?\b', r's[aá]ndwich(es)?\b', r'\btostas?\b', r'\btostadas?\b']),
    (3, [r'\bsopas?\b', r'\bcrema de(?!\s+(cacahuete|avellanas?|almendras?|chocolate|orejones))\b',
         r'\bconsom[eé]\b', r'\bcaldos?\b', r'\bgazpacho\b', r'\bvichyssoise\b']),
    (26, [r'\bhelados?\b', r'\bnatillas?\b', r'\bflanes?\b', r'\bflan\b', r'\bmousse\b']),
    (27, [r'\bporridge\b', r'\barroz con leche\b', r'\bgachas\b']),
    (29, [r'\btrufas?\b', r'\bbombones?\b', r'\bpralin[eé]s?\b']),
    (30, [r'\bmagdalenas?\b', r'\bmuffins?\b', r'\bcupcakes?\b']),
    (31, [r'\bgalletas?\b', r'\bcookies?\b']),
    (28, [r'\btartas?\b', r'\bpud[ií]n(es)?\b', r'\bbizcochos?\b', r'\bcheesecakes?\b']),
    (33, [r'\bbatidos?\b', r'\bsmoothies?\b', r'\blicuados?\b']),
    (38, [r'\bchocolatinas?\b', r'\bbarritas? de chocolate\b', r'\btabletas? de chocolate\b']),
]

NAME_KEYWORD_RULES = [
    (category_id, [re.compile(p, re.IGNORECASE) for p in patterns])
    for category_id, patterns in _RAW_NAME_RULES
]


def classify_by_name(name):
    """Devuelve el primer DishCategory.id cuyo patrón coincide con el nombre, o None."""
    for category_id, patterns in NAME_KEYWORD_RULES:
        if any(p.search(name) for p in patterns):
            return category_id
    return None


# --- Exportación de candidatos ambiguos (para revisión manual) --------------
#
# Estas categorías comparten ingrediente pero se distinguen por corte/
# preparación, algo que ni el ingrediente ni el nombre resuelven de forma
# fiable (ej. "Pollo con champiñones" no dice si tiene hueso). En vez de
# adivinar, se exportan como candidatos para revisión humana.
AMBIGUOUS_GROUPS = {
    'carnes': {
        'label': 'Carnes/Aves/Caza (categorías 18 Carnes sin hueso / 19 con hueso / 20 Aves / 21 Caza)',
        'category_ids': [18, 19, 20, 21],
        'food_groups': {21, 24, 29, 28, 22, 23},  # vacuno, ovino, cerdo, aves y caza, embutidos, cárnicos tratados
        'super_groups': {2},  # CARNE
    },
    'verduras': {
        'label': 'Ensaladas/Verduras (categorías 4 Ensaladas verdes / 5 Ensaladas no verdes / 6 Verduras cocidas)',
        'category_ids': [4, 5, 6],
        'food_groups': {3, 4, 9},  # verduras de hoja y setas, hortalizas de fruto, hortalizas bulbosas
        'super_groups': {12},  # VERDURAS Y HORTALIZAS
    },
}


# --- Tercer pase: grupo "carnes" resuelto por nombre del INGREDIENTE --------
#
# A diferencia de "Panes"/"Fritos" (descartadas antes), aquí el nombre del
# producto sí resuelve la ambigüedad de forma fiable: el tipo de animal
# determina Aves/Caza sin importar el corte, y para vacuno/cerdo/cordero el
# propio nombre del corte (filete/solomillo vs chuleta/costilla/pierna) indica
# con bastante fiabilidad si lleva hueso. Se evalúa en orden, primera
# coincidencia gana.
_RAW_MEAT_PRODUCT_RULES = [
    # Vísceras/paté coladas en el grupo "carnes" por etiquetado inconsistente del FoodGroup de origen.
    (22, [r'h[íi]gado', r'\bpat[eé]\b']),
    # Aves: el tipo de ave manda, independientemente del corte.
    (20, [r'\bpollo\b', r'\bpavo\b', r'\bpava\b', r'\bgallina\b', r'\bpularda\b']),
    # Caza: conejo se trata convencionalmente junto a la caza en las tablas españolas.
    (21, [r'\bconejo\b']),
    # Frase explícita, máxima prioridad tras aves/caza.
    (18, [r'\bsin\s+hueso\b', r'\bdeshuesad[oa]\b']),
    (19, [r'\bcon\s+(el\s+)?hueso\b']),
    # Cortes sin hueso (filetes, embutidos y curados, que no tienen hueso por naturaleza).
    (18, [
        r'\bfilete', r'\bsolomillo', r'\bbistec', r'\bpicad[ao]', r'\bmagr[ao]', r'\bgras[ao]\b',
        r'\bsolo\s+carne\b', r'\bredondo\b', r'\bcarpaccio\b', r'\bjam[oó]n', r'\bfiambre',
        r'\bchorizo', r'\bsalchich', r'\bbacon\b', r'\btocino', r'\bpanceta\b', r'\bembuchado\b',
        r'\bcecina\b', r'\blac[oó]n\b', r'\bchistorra\b', r'\blonganiza\b', r'\bbutifarra\b',
        r'\bmortadela\b', r'\bsalami\b', r'\bsobrasada\b', r'\bhamburguesa\b',
    ]),
    # Cortes con hueso (piezas enteras/con hueso habituales en carnicería).
    (19, [
        r'\bchuleta', r'\bcostilla', r'\bpaletilla\b', r'\bpierna\b', r'\bpecho\b', r'\brabo\b',
        r'\bcabeza\b', r'\baguja\b', r'\bpaleta\b',
    ]),
]

MEAT_PRODUCT_NAME_RULES = [
    (category_id, [re.compile(p, re.IGNORECASE) for p in patterns])
    for category_id, patterns in _RAW_MEAT_PRODUCT_RULES
]


def classify_meat_by_product_name(product_name):
    """Devuelve la DishCategory (18/19/20/21/22) según el nombre del ingrediente dominante, o None."""
    if not product_name:
        return None
    for category_id, patterns in MEAT_PRODUCT_NAME_RULES:
        if any(p.search(product_name) for p in patterns):
            return category_id
    return None


# --- Tercer pase: grupo "verduras" resuelto por nombre del PLATO ------------
#
# Aquí el ingrediente no sirve (un tomate está igual en una ensalada que en
# un salteado); lo que distingue Ensaladas verdes/no verdes de Verduras
# cocidas es la preparación, que sí está en el nombre del plato. "Ensalada"
# en el nombre decide si es cruda; dentro de las ensaladas, que el
# ingrediente dominante sea una hoja verde decide verde/no verde.
_LEAFY_GREEN_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r'\blechuga', r'\bcan[oó]nigos?\b', r'\br[uú]cula\b', r'\bescarola\b', r'\bespinaca',
    r'\bberros?\b', r'\bendibias?\b', r'\bbrotes?\b',
]]

_COOKED_VEG_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r'\bsaltead[oa]', r'\bal\s+vapor\b', r'\bcocid[oa]', r'\bguisad[oa]', r'\basad[oa]',
    r'\bgratinad[oa]', r'\brehogad[oa]', r'\bhervid[oa]', r'\ba\s+la\s+plancha\b', r'\ben\s+salsa\b',
    r'\bbechamel\b', r'\bpur[eé]\b', r'\bal\s+horno\b',
    # Nota: "relleno/rellena" se descarta deliberadamente aquí: no es específico de
    # verdura (ej. "Pollo relleno de espinacas" es un plato de pollo, no de verdura).
]]

ENSALADA_PATTERN = re.compile(r'\bensaladas?\b', re.IGNORECASE)


def classify_veg_group(dish_name, dominant_product_name):
    """Devuelve la DishCategory (4/5/6) para el grupo 'verduras', o None si no hay señal clara."""
    if ENSALADA_PATTERN.search(dish_name):
        if dominant_product_name and any(p.search(dominant_product_name) for p in _LEAFY_GREEN_PATTERNS):
            return 4  # Ensaladas verdes
        return 5  # Ensaladas no verdes
    if any(p.search(dish_name) for p in _COOKED_VEG_PATTERNS):
        return 6  # Verduras (rehogadas, cocidas, asadas)
    return None
