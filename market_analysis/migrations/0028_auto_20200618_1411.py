# Generated by Django 2.2.5 on 2020-06-18 14:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0027_auto_20200610_1555'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='symbol',
            name='entry_strategy',
        ),
        migrations.RemoveField(
            model_name='symbol',
            name='exit_strategy',
        ),
        migrations.AddField(
            model_name='strategy',
            name='exit_strategy',
            field=models.ForeignKey(blank=True, limit_choices_to={'strategy_type': 'ET'}, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='strategy', to='market_analysis.Strategy'),
        ),
        migrations.AddField(
            model_name='symbol',
            name='strategy',
            field=models.ManyToManyField(blank=True, limit_choices_to={'strategy_type': 'ET'}, related_name='symbols', to='market_analysis.Strategy'),
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M60', '60 Minute'), ('M5', '5 Minute'), ('1D', '1 Day'), ('M15', '15 Minute'), ('M10', '10 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='entry_type',
            field=models.CharField(blank=True, choices=[('EX', 'Exit'), ('ET', 'Entry')], default='', max_length=10),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('CO', 'Completed'), ('RE', 'Rejected'), ('CA', 'Cancelled'), ('OP', 'Open')], default='OP', max_length=10),
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
            field=models.CharField(choices=[('PR', 'Primary'), ('SP', 'Support'), ('SC', 'Secondary')], default='SU', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='strategy_type',
            field=models.CharField(choices=[('EX', 'Exit'), ('ET', 'Entry')], default='ET', max_length=20),
        ),
    ]
