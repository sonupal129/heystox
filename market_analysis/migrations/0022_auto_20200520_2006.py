# Generated by Django 2.2.5 on 2020-05-20 20:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0021_auto_20200510_2304'),
    ]

    operations = [
        migrations.CreateModel(
            name='Strategy',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('strategy_name', models.CharField(blank=True, max_length=200, null=True)),
                ('strategy_location', models.CharField(max_length=500)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M10', '10 Minute'), ('M15', '15 Minute'), ('1D', '1 Day'), ('M60', '60 Minute'), ('M5', '5 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='indicator',
            name='indicator_type',
            field=models.CharField(choices=[('PR', 'PRIMARY'), ('SC', 'SECONDARY'), ('SP', 'SUPPORTING')], default='SC', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('OP', 'Open'), ('RE', 'Rejected'), ('CA', 'Cancelled'), ('CO', 'Completed')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTYBNK', 'Nifty Bank'), ('NFTY', 'Nifty')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('SELL', 'SELL'), ('SB', 'SIDEWAYS_BUY'), ('SS', 'SIDEWAYS_SELL'), ('BUY', 'BUY')], default='BUY', max_length=20),
        ),
    ]
