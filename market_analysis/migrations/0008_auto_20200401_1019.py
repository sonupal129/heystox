# Generated by Django 2.2.5 on 2020-04-01 10:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0007_auto_20200327_2117'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now=True)),
                ('modified_at', models.DateTimeField(auto_now_add=True)),
                ('order_id', models.IntegerField(blank=True, null=True)),
                ('entry_time', models.DateTimeField(blank=True, null=True)),
                ('price', models.FloatField(blank=True, null=True)),
                ('transaction_type', models.CharField(blank=True, max_length=10, null=True)),
                ('status', models.CharField(choices=[('OP', 'Open'), ('RE', 'Rejected'), ('CA', 'Cancelled'), ('CO', 'Completed')], default='OP', max_length=10)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='orderbook',
            name='quantity',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M15', '15 Minute'), ('M5', '5 Minute'), ('M60', '60 Minute'), ('1D', '1 Day'), ('M10', '10 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='orderbook',
            name='entry_type',
            field=models.CharField(blank=True, choices=[('BUY', 'BUY'), ('SELL', 'SELL')], max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTY', 'Nifty'), ('NFTYBNK', 'Nifty Bank')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='sortedstockslist',
            name='entry_type',
            field=models.CharField(choices=[('SB', 'SIDEWAYS_BUY'), ('BUY', 'BUY'), ('SELL', 'SELL'), ('SS', 'SIDEWAYS_SELL')], default='BUY', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategytimestamp',
            name='timestamp',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.DeleteModel(
            name='Orders',
        ),
        migrations.AddField(
            model_name='order',
            name='order_book',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='market_analysis.OrderBook'),
        ),
    ]
