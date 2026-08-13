from dataclasses import dataclass, field
from datetime import date


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
