# Generated by Django 2.2.5 on 2020-08-30 15:15

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0049_auto_20200822_1944'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M5', '5 Minute'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('1D', '1 Day'), ('1H', '1 Hour')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='entry_type',
            field=models.CharField(choices=[('SELL', 'SELL'), ('BUY', 'BUY')], default='BUY', max_length=10),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='timeframe',
            field=models.CharField(blank=True, choices=[('M5', '5 Minute'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('1D', '1 Day'), ('1H', '1 Hour')], max_length=5, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='entry_type',
            field=models.CharField(blank=True, choices=[('EX', 'Exit'), ('ET', 'Entry')], default='', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('CA', 'Cancelled'), ('CO', 'Completed'), ('RE', 'Rejected'), ('OP', 'Open')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='transaction_type',
            field=models.CharField(blank=True, choices=[('SELL', 'SELL'), ('BUY', 'BUY')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTYBNK', 'Nifty Bank'), ('NFTY', 'Nifty')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('SELL', 'SELL'), ('BUY', 'BUY')], default='BUY', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='priority_type',
            field=models.CharField(choices=[('PR', 'Primary'), ('SC', 'Secondary'), ('SP', 'Support')], default='SU', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='strategy_type',
            field=models.CharField(choices=[('EX', 'Exit'), ('ET', 'Entry')], default='ET', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='timeframe',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('M5', '5 Minute'), ('M15', '15 Minute'), ('M60', '60 Minute'), ('M10', '10 Minute'), ('M30', '30 Minute'), ('1D', '1 Day'), ('1H', '1 Hour')], max_length=24, null=True),
        ),
        migrations.AlterField(
            model_name='symbol',
            name='trade_manually',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('SELL', 'SELL'), ('BUY', 'BUY')], max_length=8, null=True),
        ),
        migrations.AlterField(
            model_name='symbol',
            name='trade_realtime',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('SELL', 'SELL'), ('BUY', 'BUY')], help_text='Enabling this will call realtime strategies for trading', max_length=8, null=True),
        ),
    ]
