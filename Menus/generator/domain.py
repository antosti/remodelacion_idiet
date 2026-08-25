from dataclasses import dataclass, field
from datetime import date

from Intakes.models import Intake


ROLE_LABELS = {
    'single': 'Plato',
    'starter': 'Entrante',
    'main': 'Plato principal',
    'dessert': 'Postre',
}


@dataclass(frozen=True)
class DishCandidate:
    dish_id: int
    name: str
    kcal_100g: float
    prot_100g: float
    fat_100g: float
    carb_100g: float
    # Racion real del plato en gramos (Dish.dish_category_size, o media de la
    # ingesta si no tiene tamano asignado); None si no hay ningun dato.
    portion_grams: float | None = None


@dataclass
class NutritionTarget:
    kcal: float
    prot_g: float
    fat_g: float
    carb_g: float


@dataclass
class MealSlotConfig:
    """Un 'momento' del dia a incluir en la dieta: una toma suelta (kind='single')
    o un grupo tipo comida/cena (kind='group') con entrante/principal/postre."""
    key: str
    label: str
    kind: str
    intakes: dict = field(default_factory=dict)  # role -> Intake
    include_starter: bool = False
    include_dessert: bool = False

    def active_roles(self):
        if self.kind == 'single':
            return ['single'] if 'single' in self.intakes else []

        roles = ['main'] if 'main' in self.intakes else []
        if self.include_starter and self.intakes.get('starter'):
            roles.append('starter')
        if self.include_dessert and self.intakes.get('dessert'):
            roles.append('dessert')
        return roles


@dataclass
class DietConfig:
    days: int
    start_date: date
    meal_slots: list
    target: NutritionTarget
    max_portion_grams: int | None = None
    # Tamano de racion (DishCategorySize.Size, ej. 'S') que fuerza la racion
    # de cada plato segun su propia categoria; ver Menus.generator.pools.
    portion_size: str | None = None


def serialize_config(config):
    """Config -> dict serializable en JSON, para poder rehacer una dieta mas
    tarde con exactamente los mismos parametros (ver Menus.models.Menu.generation_config)."""
    return {
        'meal_slots': [
            {
                'key': slot.key,
                'label': slot.label,
                'kind': slot.kind,
                'intakes': {role: intake.id for role, intake in slot.intakes.items()},
                'include_starter': slot.include_starter,
                'include_dessert': slot.include_dessert,
            }
            for slot in config.meal_slots
        ],
        'target': {
            'kcal': config.target.kcal,
            'prot_g': config.target.prot_g,
            'fat_g': config.target.fat_g,
            'carb_g': config.target.carb_g,
        },
        'portion_size': config.portion_size,
    }


def deserialize_config(data, days, start_date):
    """Inverso de serialize_config: reconstruye un DietConfig a partir del
    JSON guardado en Menu.generation_config y del rango de fechas a usar."""
    intake_ids = {
        intake_id
        for slot in data['meal_slots']
        for intake_id in slot['intakes'].values()
    }
    intakes_by_id = {intake.id: intake for intake in Intake.objects.filter(id__in=intake_ids)}

    meal_slots = [
        MealSlotConfig(
            key=slot['key'],
            label=slot['label'],
            kind=slot['kind'],
            intakes={
                role: intakes_by_id[intake_id]
                for role, intake_id in slot['intakes'].items()
                if intake_id in intakes_by_id
            },
            include_starter=slot['include_starter'],
            include_dessert=slot['include_dessert'],
        )
        for slot in data['meal_slots']
    ]

    return DietConfig(
        days=days,
        start_date=start_date,
        meal_slots=meal_slots,
        target=NutritionTarget(**data['target']),
        portion_size=data.get('portion_size'),
    )


def day_totals(day_menu):
    """day_menu: dict[slot_key][role] -> (DishCandidate, quantity_grams) | None"""
    kcal = prot = fat = carb = 0.0
    for courses in day_menu.values():
        for entry in courses.values():
            if entry is None:
                continue
            candidate, qty = entry
            factor = qty / 100.0
            kcal += candidate.kcal_100g * factor
            prot += candidate.prot_100g * factor
            fat += candidate.fat_100g * factor
            carb += candidate.carb_100g * factor
    return kcal, prot, fat, carb
