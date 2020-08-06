# Generated by Django 2.2.5 on 2020-07-20 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0035_auto_20200712_1802'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M60', '60 Minute'), ('1D', '1 Day'), ('M5', '5 Minute'), ('M30', '30 Minute'), ('M10', '10 Minute'), ('1H', '1 Hour'), ('M15', '15 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='entry_type',
            field=models.CharField(choices=[('BUY', 'BUY'), ('SELL', 'SELL')], default='BUY', max_length=10),
        ),
        migrations.AlterField(
            model_name='deployedstrategies',
            name='timeframe',
            field=models.CharField(choices=[('M60', '60 Minute'), ('1D', '1 Day'), ('M5', '5 Minute'), ('M30', '30 Minute'), ('M10', '10 Minute'), ('1H', '1 Hour'), ('M15', '15 Minute')], default='M5', max_length=5),
        ),
        migrations.AlterField(
            model_name='order',
            name='entry_type',
            field=models.CharField(blank=True, choices=[('ET', 'Entry'), ('EX', 'Exit')], default='', max_length=10),
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
            name='entry_type',
            field=models.CharField(choices=[('BUY', 'BUY'), ('SELL', 'SELL')], default='BUY', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='backtesting_ready',
            field=models.BooleanField(default=False, help_text='Check if you think that strategy is ready for backtesting, Please use this function carefully as this put burden on server'),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='strategy_type',
            field=models.CharField(choices=[('ET', 'Entry'), ('EX', 'Exit')], default='ET', max_length=20),
        ),
    ]