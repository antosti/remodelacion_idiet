import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Products', '0004_productexcluded_productinactive'),
        ('Clients', '0004_alter_client_address'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='productexcluded',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='productexcluded',
            name='user',
        ),
        migrations.AddField(
            model_name='productexcluded',
            name='client',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='excluded_products', to='Clients.client'),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='productexcluded',
            unique_together={('client', 'product')},
        ),
    ]
