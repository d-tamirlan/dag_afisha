from django.db import models
from django.db.models.signals import post_save
from django.core.mail import send_mail
from django.conf import settings


class TelegramUser(models.Model):
    def __init__(self, *args, **kwargs):
        super(TelegramUser, self).__init__(*args, **kwargs)

    account_id = models.IntegerField('ID телеграм аккаунта', default=0)
    chat_id = models.IntegerField('ID чата с ботом', default=0)
    is_bot = models.BooleanField('Бот', default=False)
    first_name = models.CharField('Имя', max_length=255, null=True, blank=True)
    last_name = models.CharField('Фамилия', max_length=255, null=True, blank=True)
    username = models.CharField('Имя пользователя', max_length=255, null=True, blank=True)
    add_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    class Meta:
        ordering = ['-add_date']
        verbose_name = 'Пользователя телеграм'
        verbose_name_plural = 'Пользователи телеграма'

    @staticmethod
    def send_notice(sender, instance, *args, **kwargs):
        """ send notice when new user joined bot """
        print('send_notice')
        email_msg = f"""
            Username: {instance.username}
            First name: {instance.first_name}
            Last name: {instance.last_name}
            Is bot: {instance.is_bot}
        """

        send_mail(
            'Новый пользователь',
            email_msg,
            settings.DEFAULT_FROM_EMAIL,
            ['konoor@yandex.ru'],
            fail_silently=False,
        )


post_save.connect(TelegramUser.send_notice, sender=TelegramUser)


class Cinema(models.Model):
    title = models.CharField('Название', max_length=255, default='')
    description = models.TextField('Информация', max_length=5000, default='')
    schedule_url = models.URLField('Ссылка на график', max_length=500, default='')
    img = models.ImageField('Фото', upload_to='cinemas/', default='', blank=True)
    add_date = models.DateTimeField('Дата добавления', auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-add_date']
        verbose_name = 'Кинотеатр'
        verbose_name_plural = 'Кинотеатры'


class FilmSchedule(models.Model):
    cinema = models.ForeignKey(Cinema, verbose_name='Кинотеатр', null=True, on_delete=models.CASCADE)
    name = models.CharField('Название', max_length=255, default='')
    time = models.CharField('Время', max_length=255, default='')
    price = models.PositiveIntegerField('Цена', default=0)
    film_format = models.CharField('Формат', max_length=255, default='')
    date = models.DateField('Дата', default='')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-date']
        verbose_name = 'График'
        verbose_name_plural = 'Графики'


class Storage(models.Model):
    account_id = models.PositiveIntegerField('ID телеграм аккаунта', default=0)
    key = models.CharField('Ключ', max_length=500, default='')
    value = models.TextField('Значение', max_length=5000, default='')
    add_date = models.DateTimeField('Дата добавления', auto_now=True)

    def __str__(self):
        return self.key

    class Meta:
        ordering = ['-add_date']
        verbose_name = 'Данные'
        verbose_name_plural = 'Хранилище'
