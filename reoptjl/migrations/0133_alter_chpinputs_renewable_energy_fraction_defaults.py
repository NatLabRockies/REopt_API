import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reoptjl', '0132_chpoutputs_pwf_fuel_chpoutputs_pwf_fuel2_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chpinputs',
            name='fuel_renewable_energy_fraction',
            field=models.FloatField(blank=True, help_text='Fraction of the CHP fuel considered renewable. Default depends on fuel type (1.0 for landfill_bio_gas, otherwise 0.0).', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='chpinputs',
            name='fuel2_renewable_energy_fraction',
            field=models.FloatField(blank=True, help_text='Fraction of the CHP fuel2_type considered renewable. Default depends on fuel2_type (1.0 for landfill_bio_gas, otherwise 0.0).', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1)]),
        ),
    ]
