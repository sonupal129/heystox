# Generated by Django 2.2.5 on 2020-05-25 16:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0022_auto_20200520_2006'),
    ]

    operations = [
        migrations.AddField(
            model_name='symbol',
            name='strategy',
            field=models.ManyToManyField(related_name='symbols', to='market_analysis.Strategy'),
        ),
    ]
