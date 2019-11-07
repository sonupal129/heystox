# Generated by Django 2.2.5 on 2019-11-04 23:01

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('market_analysis', '0015_auto_20191031_2210'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='earning',
            name='account',
        ),
        migrations.AddField(
            model_name='earning',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='earnings', to='market_analysis.UserProfile'),
        ),
        migrations.AlterField(
            model_name='candle',
            name='candle_type',
            field=models.CharField(choices=[('M60', '60 Minute'), ('M10', '10 Minute'), ('1D', '1 Day'), ('M5', '5 Minute'), ('M15', '15 Minute')], default=None, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_profile', to=settings.AUTH_USER_MODEL),
        ),
    ]