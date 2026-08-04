from django.db import migrations, models
import django.contrib.postgres.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('reoptjl', '0116_alter_apimeta_api_key_alter_apimeta_job_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chpinputs',
            name='meta',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='CHPInputs', to='reoptjl.apimeta'),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='existing_kw',
            field=models.FloatField(blank=True, default=0, help_text='Existing CHP electric capacity (based on rated electric power)', validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100000.0)]),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='fuel_cost_escalation_rate_fraction',
            field=models.FloatField(blank=True, help_text='Annual nominal chp fuel cost escalation rate, as a decimal.', null=True, validators=[django.core.validators.MinValueValidator(-1.0), django.core.validators.MaxValueValidator(1.0)]),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='name',
            field=models.TextField(blank=True, default='CHP', help_text='CHP description for distinguishing between multiple CHP models'),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='operating_reserve_required_fraction',
            field=models.FloatField(blank=True, help_text='Only applicable when off_grid_flag=True. Required operating reserves applied to each timestep as a fraction of CHP generation serving load in that timestep.', null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1.0)]),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='production_factor_series',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(blank=True), blank=True, default=list, help_text='Optional user-defined production factors. Must be normalized to units of kW-AC/kW-AC nameplate, representing the AC power (kW) output per 1 kW-AC of CHP capacity in each time step. The series must be one year (January through December) of hourly, 30-minute, or 15-minute data.', size=None),
        ),
        migrations.AddField(
            model_name='chpinputs',
            name='ramp_rate_fraction_per_hour',
            field=models.FloatField(blank=True, default=1.0, help_text='Maximum rate of change in electric production per hour as a fraction of size_kw [kW/size_kw/hour].', validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(1000.0)]),
        ),
        migrations.AlterField(
            model_name='chpoutputs',
            name='meta',
            field=models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='CHPOutputs', to='reoptjl.apimeta'),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='annual_electric_production_kwh_bau',
            field=models.FloatField(blank=True, help_text='Electric energy produced in a year by the existing CHP system in BAU [kWh]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='annual_fuel_consumption_mmbtu_bau',
            field=models.FloatField(blank=True, help_text='Fuel consumed in a year by the existing CHP system in BAU [MMBtu]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='annual_thermal_production_mmbtu_bau',
            field=models.FloatField(blank=True, help_text='Thermal energy produced in a year by the existing CHP system in BAU [MMBtu]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='lifecycle_fuel_cost_after_tax_bau',
            field=models.FloatField(blank=True, help_text='Present value of cost of fuel consumed by the existing CHP system in BAU, after tax [$]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='lifecycle_standby_cost_after_tax_bau',
            field=models.FloatField(blank=True, help_text='Present value of all CHP standby charges for the existing CHP system in BAU, after tax.', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='name',
            field=models.TextField(blank=True, default='CHP', help_text='CHP description for distinguishing between multiple CHP models'),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='size_kw_bau',
            field=models.FloatField(blank=True, help_text='Power capacity size of the existing CHP system in BAU [kW]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='year_one_fuel_cost_after_tax_bau',
            field=models.FloatField(blank=True, help_text='Cost of fuel consumed by the existing CHP system in year one in BAU, after tax [$]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='year_one_fuel_cost_before_tax_bau',
            field=models.FloatField(blank=True, help_text='Cost of fuel consumed by the existing CHP system in year one in BAU [$]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='year_one_standby_cost_after_tax_bau',
            field=models.FloatField(blank=True, help_text='CHP standby charges in year one for the existing CHP system in BAU, after tax [$]', null=True),
        ),
        migrations.AddField(
            model_name='chpoutputs',
            name='year_one_standby_cost_before_tax_bau',
            field=models.FloatField(blank=True, help_text='CHP standby charges in year one for the existing CHP system in BAU [$]', null=True),
        ),
    ]
