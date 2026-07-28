from django.db import migrations


SUPER_GROUPS = (
    'ARROZ',
    'CARNE',
    'CEREALES',
    'FRUTA',
    'HUEVOS',
    'LACTEOS',
    'LEGUMBRES',
    'PASTA',
    'PATATAS',
    'PESCADO',
    'PROTEINAS',
    'VERDURAS Y HORTALIZAS',
    'FRUTOS SECOS',
)


def create_super_groups(apps, schema_editor):
    super_group_model = apps.get_model('SuperGroup', 'SuperGroup')
    database_alias = schema_editor.connection.alias
    for name in SUPER_GROUPS:
        super_group_model.objects.using(database_alias).get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('SuperGroup', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_super_groups,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
