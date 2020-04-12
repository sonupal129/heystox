# Generated by Django 2.2.5 on 2020-04-01 17:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0011_auto_20200401_1400'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderbook',
            name='date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M15', '15 Minute'), ('1D', '1 Day'), ('M5', '5 Minute'), ('M10', '10 Minute'), ('M60', '60 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('CO', 'Completed'), ('OP', 'Open'), ('RE', 'Rejected'), ('CA', 'Cancelled')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='orderbook',
            name='entry_type',
            field=models.CharField(blank=True, choices=[('SELL', 'SELL'), ('BUY', 'BUY')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTY', 'Nifty'), ('NFTYBNK', 'Nifty Bank')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('SB', 'SIDEWAYS_BUY'), ('SELL', 'SELL'), ('BUY', 'BUY'), ('SS', 'SIDEWAYS_SELL')], default='BUY', max_length=20),
        ),
    ]
