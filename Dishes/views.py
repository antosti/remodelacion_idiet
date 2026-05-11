from django.shortcuts import render, redirect

from Intakes.models import Intake
from Dishes.models import Dish
from Micronutrients.models import Micronutrient


MICRONUTRIENT_SECTIONS = [
    {
        'title': 'General',
        'ids': [1, 69, 2, 70, 71, 4, 5, 6, 7],
    },
    {
        'title': 'Vitaminas y otros',
        'ids': [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 72, 23],
    },
    {
        'title': 'Minerales',
        'ids': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38],
    },
    {
        'title': 'Ácidos grasos',
        'ids': list(range(39, 69)),
    },
]


MICRONUTRIENTS_IN_GRAMS = {1, 2, 4, 5, 6, 68, 69, 70, 71}
MICRONUTRIENTS_IN_UG = {8, 15, 16, 17, 19, 22, 32, 33, 37, 38, 72}


def get_micronutrient_unit(micronutrient_id):
    if micronutrient_id in MICRONUTRIENTS_IN_GRAMS:
        return 'g'

    if micronutrient_id in MICRONUTRIENTS_IN_UG:
        return 'ug'

    return 'mg'


def get_micronutrient_sections():
    all_ids = []

    for section in MICRONUTRIENT_SECTIONS:
        all_ids += section['ids']

    micronutrients = Micronutrient.objects.filter(id__in=all_ids)
    micronutrients_by_id = {micronutrient.id: micronutrient for micronutrient in micronutrients}

    sections = []

    for section in MICRONUTRIENT_SECTIONS:
        section_micronutrients = []

        for micronutrient_id in section['ids']:
            micronutrient = micronutrients_by_id.get(micronutrient_id)

            if micronutrient:
                micronutrient.unit = get_micronutrient_unit(micronutrient.id)
                section_micronutrients.append(micronutrient)

        sections.append({
            'title': section['title'],
            'micronutrients': section_micronutrients,
        })

    return sections


def create_dish(request):
    intakes = Intake.objects.all().order_by('order')
    micronutrient_sections = get_micronutrient_sections()

    if request.method == 'POST':
        Dish.objects.create(
            name=request.POST.get('recipe_name'),
            recipe_elaboration=request.POST.get('description'),
            language='es',
        )

        return redirect('create_dish')

    return render(request, 'admin/create_dish.html', {
        'intakes': intakes,
        'micronutrient_sections': micronutrient_sections,
    })