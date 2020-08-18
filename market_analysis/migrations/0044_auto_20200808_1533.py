# Generated by Django 2.2.5 on 2020-08-08 15:33

from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0043_auto_20200726_1958'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='stratrgy',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to='market_analysis.DeployedStrategies'),
        ),
    ]