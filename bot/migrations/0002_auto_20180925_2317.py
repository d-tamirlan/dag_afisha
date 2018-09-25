# Generated by Django 2.1.1 on 2018-09-25 20:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='telegramuser',
            name='user',
        ),
        migrations.AddField(
            model_name='telegramuser',
            name='chat_id',
            field=models.IntegerField(default=0, verbose_name='ID чата с ботом'),
        ),
        migrations.AlterField(
            model_name='telegramuser',
            name='first_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Имя'),
        ),
        migrations.AlterField(
            model_name='telegramuser',
            name='last_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Фамилия'),
        ),
        migrations.AlterField(
            model_name='telegramuser',
            name='username',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Имя пользователя'),
        ),
    ]