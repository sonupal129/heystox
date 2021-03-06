# Generated by Django 2.2.5 on 2020-03-27 21:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0005_auto_20200317_0038'),
    ]

    operations = [
        migrations.CreateModel(
            name='Orders',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('modified_at', models.DateTimeField(auto_now_add=True)),
                ('order_id', models.IntegerField(blank=True, null=True)),
                ('entry_time', models.DateTimeField(blank=True, null=True)),
                ('price', models.FloatField(blank=True, null=True)),
                ('transaction_type', models.CharField(blank=True, max_length=10, null=True)),
                ('status', models.CharField(choices=[('CO', 'Completed'), ('RE', 'Rejected'), ('CA', 'Cancelled'), ('OP', 'Open')], default='OP', max_length=10)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='orderbook',
            name='entry_time',
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M60', '60 Minute'), ('M10', '10 Minute'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M5', '5 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTYBNK', 'Nifty Bank'), ('NFTY', 'Nifty')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('SS', 'SIDEWAYS_SELL'), ('BUY', 'BUY'), ('SELL', 'SELL'), ('SB', 'SIDEWAYS_BUY')], default='BUY', max_length=20),
        ),
    ]
