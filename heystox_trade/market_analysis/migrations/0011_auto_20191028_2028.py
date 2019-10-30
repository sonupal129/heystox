# Generated by Django 2.2.5 on 2019-10-28 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0010_auto_20191028_2017'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M5', '5 Minute'), ('1D', '1 Day'), ('M60', '60 Minute'), ('M10', '10 Minute'), ('M15', '15 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='earning',
            name='opening_balance',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='earning',
            name='profit_loss',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Profit & Loss'),
        ),
    ]
