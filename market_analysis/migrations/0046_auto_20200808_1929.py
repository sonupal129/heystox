# Generated by Django 2.2.5 on 2020-08-08 19:29

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0045_auto_20200808_1626'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M60', '60 Minute'), ('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('M5', '5 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='timeframe',
            field=models.CharField(choices=[('M60', '60 Minute'), ('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('M5', '5 Minute')], default='M5', max_length=5),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('OP', 'Open'), ('CA', 'Cancelled'), ('CO', 'Completed'), ('RE', 'Rejected')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='added',
            field=models.CharField(choices=[('ML', 'Manually'), ('AT', 'Automatically')], default='AT', max_length=10),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='priority_type',
            field=models.CharField(choices=[('SC', 'Secondary'), ('SP', 'Support'), ('PR', 'Primary')], default='SU', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='timeframe',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('M60', '60 Minute'), ('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('M5', '5 Minute')], max_length=24, null=True),
        ),
        migrations.AlterField(
            model_name='symbol',
            name='trade_manually',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('SELL', 'SELL'), ('BUY', 'BUY')], max_length=8, null=True),
        ),
    ]
