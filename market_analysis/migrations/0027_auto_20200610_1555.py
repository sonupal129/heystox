# Generated by Django 2.2.5 on 2020-06-10 15:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0026_auto_20200610_1201'),
    ]

    operations = [
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M5', '5 Minute'), ('1D', '1 Day'), ('M10', '10 Minute'), ('M60', '60 Minute'), ('M15', '15 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('CA', 'Cancelled'), ('CO', 'Completed'), ('RE', 'Rejected'), ('OP', 'Open')], default='OP', max_length=10),
        ),
        migrations.AlterField(
            model_name='premarketorderdata',
            name='sector',
            field=models.CharField(choices=[('NFTY', 'Nifty'), ('NFTYBNK', 'Nifty Bank')], default='NFTYBNK', max_length=20),
        ),
        migrations.AlterField(
            model_name='strategy',
            name='priority_type',
            field=models.CharField(choices=[('SP', 'Support'), ('SC', 'Secondary'), ('PR', 'Primary')], default='SU', max_length=20),
        ),
    ]