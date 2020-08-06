# Generated by Django 2.2.5 on 2020-07-24 09:25

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0038_auto_20200720_2324'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='symbol',
            name='strategy',
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M5', '5 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='entry_type',
            field=models.CharField(choices=[('BUY', 'BUY'), ('SELL', 'SELL')], default='BUY', max_length=10),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='timeframe',
            field=models.CharField(choices=[('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M5', '5 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute')], default='M5', max_length=5),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('OP', 'Open'), ('CO', 'Completed'), ('CA', 'Cancelled'), ('RE', 'Rejected')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='transaction_type',
            field=models.CharField(blank=True, choices=[('BUY', 'BUY'), ('SELL', 'SELL')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='added',
            field=models.CharField(choices=[('AT', 'Automatically'), ('ML', 'Manually')], default='AT', max_length=10),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('BUY', 'BUY'), ('SELL', 'SELL')], default='BUY', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='priority_type',
            field=models.CharField(choices=[('SC', 'Secondary'), ('PR', 'Primary'), ('SP', 'Support')], default='SU', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='strategy_for',
            field=models.CharField(choices=[('EF', 'EquityFutures'), ('EI', 'EquityIntraday')], default='EI', max_length=10),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='timeframe',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('1H', '1 Hour'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M5', '5 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute')], max_length=24, null=True),
        ),
    ]