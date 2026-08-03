from django.db import migrations


MICRONUTRIENTS = [
    # General
    (3, 'PC'),
    (1, 'Agua'),
    (2, 'Fibra'),
    (4, 'AGS totales'),
    (5, 'AGM totales'),
    (6, 'AGP totales'),
    (7, 'Colesterol'),
    # Vitaminas y otros
    (8, 'Vit A'),
    (9, 'Carotenos'),
    (10, 'Tiamina B1'),
    (11, 'Riboflavina B2'),
    (12, 'Niacina B3'),
    (13, 'Ac. Pantoténico B5'),
    (14, 'Piridoxina B6'),
    (15, 'Biotina'),
    (16, 'Ac. Fólico B9'),
    (17, 'Cobalamina B12'),
    (18, 'Vit C'),
    (19, 'Vit D'),
    (20, 'Tocoferol'),
    (21, 'Vit E'),
    (22, 'Vit K'),
    (23, 'Oxálico'),
    (72, 'Purinas'),
    # Minerales
    (24, 'Sodio'),
    (25, 'Potasio'),
    (26, 'Magnesio'),
    (27, 'Calcio'),
    (28, 'Fósforo'),
    (29, 'Hierro'),
    (30, 'Cloro'),
    (31, 'Zinc'),
    (32, 'Cobre'),
    (33, 'Manganeso'),
    (34, 'Cromo'),
    (35, 'Cobalto'),
    (36, 'Molibde'),
    (37, 'Yodo'),
    (38, 'Fluor'),
    # Ácidos grasos
    (39, 'Butírico C4:0'),
    (40, 'Caproico C6:0'),
    (41, 'Caprílico C8:0'),
    (42, 'Cáprico C10:0'),
    (43, 'Lárico C12:0'),
    (44, 'Mirístico C14:0'),
    (45, 'C15:0'),
    (46, 'C15:00'),
    (47, 'Palmítico C16:0'),
    (48, 'C17:0'),
    (49, 'C17:00'),
    (50, 'Esteárico C18:0'),
    (51, 'Araquídico C20:0'),
    (52, 'Behénico C22:0'),
    (53, 'Miristol C14:1'),
    (54, 'Palmitole C16:1'),
    (55, 'Oleico C18:1'),
    (56, 'Eicoseno C20:1'),
    (57, 'C22:1'),
    (58, 'Linoleico C18:2'),
    (59, 'Linolénico C18:3'),
    (60, 'C18:4'),
    (61, 'Araquidónico C20:4'),
    (62, 'C20:5'),
    (63, 'C22:5'),
    (64, 'C22:6'),
    (65, 'Otros satura'),
    (66, 'Otros insatura'),
    (67, 'Omega 3:0'),
    (68, 'Etanol'),
]


def seed_micronutrients(apps, schema_editor):
    Micronutrient = apps.get_model('Micronutrients', 'Micronutrient')
    db_alias = schema_editor.connection.alias

    Micronutrient.objects.using(db_alias).bulk_create(
        [
            Micronutrient(id=micronutrient_id, name=name)
            for micronutrient_id, name in MICRONUTRIENTS
        ],
        ignore_conflicts=True,
    )


def remove_micronutrients(apps, schema_editor):
    Micronutrient = apps.get_model('Micronutrients', 'Micronutrient')
    db_alias = schema_editor.connection.alias

    Micronutrient.objects.using(db_alias).filter(
        id__in=[micronutrient_id for micronutrient_id, _ in MICRONUTRIENTS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Micronutrients', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_micronutrients, remove_micronutrients),
    ]
