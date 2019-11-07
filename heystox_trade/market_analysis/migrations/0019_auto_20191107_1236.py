# Generated by Django 2.2.5 on 2019-11-07 12:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0018_auto_20191107_1209'),
    ]
    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('1D', '1 Day'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M10', '10 Minute'), ('M5', '5 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='atp',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='close',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='high',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='low',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='lower_circuit',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='ltp',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='open',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
        migrations.AlterField(
            model_name='tickerdata',
            name='upper_circuit',
            field=models.FloatField(blank=True, null=True, verbose_name='Last Traded Price'),
        ),
    ]
