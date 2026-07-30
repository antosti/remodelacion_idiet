from django.db import migrations

DEFAULT_INTAKES = [
    'Desayuno',
    'Media mañana',
    '1ª plato Comida',
    'Plato principal comida',
    'Postre',
    'Merienda',
    '1ª plato Cena',
    'Plato principal cena',
    'Recena',
    'Otros',
]


def add_default_intakes(apps, schema_editor):
    Intake = apps.get_model('Intakes', 'Intake')

    for order, name in enumerate(DEFAULT_INTAKES, start=1):
        Intake.objects.get_or_create(name=name, defaults={'order': order})


def remove_default_intakes(apps, schema_editor):
    Intake = apps.get_model('Intakes', 'Intake')
    Intake.objects.filter(name__in=DEFAULT_INTAKES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Intakes', '0004_alter_intake_order_points'),
    ]

    operations = [
        migrations.RunPython(add_default_intakes, remove_default_intakes),
    ]
