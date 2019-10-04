import os
from django.conf import settings
from itertools import groupby
from django.utils import timezone
import telebot
import requests
import logging
from bs4 import BeautifulSoup
from . import models as bot_md


dag_afisha_bot = telebot.TeleBot(settings.DAG_AFISHA_TOKEN, threaded=False)

app_dir = os.path.join(settings.BASE_DIR, __package__)
handler = logging.FileHandler(os.path.join(app_dir, 'logs.log'), encoding='utf-8')

dag_afisha_logger = logging.getLogger('dag_afisha_logger')
dag_afisha_logger.addHandler(handler)
dag_afisha_logger.setLevel(logging.DEBUG)
dag_afisha_logger.setLevel(logging.INFO)

EMOJI = {
    'back': b'\xF0\x9F\x94\x99'.decode('utf-8')
}


class BaseMessageHandler:
    keyboard_row_width = 0

    def __init__(self, message):
        self.message = message
        self.dispatch()

    def dispatch(self):
        """ entry point """
        # Checking and creating new user need only for /start command
        # If it's not /start command  then just response on message
        if self.message.text != '/start':
            return self.send_response()

        chat_id = self.message.chat.id

        bot_user, created = bot_md.TelegramUser.objects.get_or_create(
            account_id=self.message.from_user.id,
            defaults={
                'chat_id': chat_id,
                'is_bot': self.message.from_user.is_bot,
                'first_name': self.message.from_user.first_name,
                'last_name': self.message.from_user.last_name,
                'username': self.message.from_user.username,
            }
        )

        # if chat_id was changed then set new chat_id,
        # chat_id need for sending messages for users
        if bot_user.chat_id != chat_id:
            bot_user.chat_id = chat_id
            bot_user.save()

        self.send_response()

    def send_response(self):
        """ sending response from bot """
        raise NotImplementedError

    def get_markup(self, chunk_btn_texts):
        markup = telebot.types.ReplyKeyboardMarkup(row_width=self.keyboard_row_width, resize_keyboard=True)
        for btn_texts in chunk_btn_texts:
            markup.add(*btn_texts)

        return markup


class Cinemas(BaseMessageHandler):
    model = bot_md.Cinema
    keyboard_row_width = 3
    response_msg = 'Выберите кинотеатр'

    def __init__(self, message):
        self.message = message
        self.selected_cinema = self.get_selected_cinema()
        self.dispatch()

    def get_selected_cinema(self):
        """ Getting selected cinema from storage
        if there is no selected cinema, then return None """
        try:
            selected_cinema = bot_md.Storage.objects.get(
                account_id=self.message.from_user.id,
                key='selected_cinema',
            )
        except bot_md.Storage.DoesNotExist:
            return None

        return bot_md.Cinema.objects.get(title=selected_cinema.value)

    def send_response(self):
        chunk_cinemas = self.get_chunk_cinemas()
        markup = self.get_markup(chunk_cinemas)

        dag_afisha_bot.send_message(
            self.message.chat.id,
            self.response_msg,
            reply_markup=markup
        )

    def get_chunk_cinemas(self):
        """ chunk cinemas form table display in telegram keyboard
        :return chunk_cinemas
        """
        cinemas = self.model.objects.values_list('title', flat=True)

        chunk_cinemas = (
            tuple(cinemas[i:i + self.keyboard_row_width])
            for i in range(0, len(cinemas), self.keyboard_row_width)
        )

        return chunk_cinemas


class Info(Cinemas):
    def dispatch(self):
        # if selected cinema doesn't exist then send cinemas for selecting
        if not self.selected_cinema:
            return super(Info, self).send_response()

        return self.send_response()

    def send_response(self):
        dag_afisha_bot.send_message(
            self.message.chat.id,
            self.selected_cinema.description,
        )


class Week(BaseMessageHandler):
    model = bot_md.Cinema
    __week_days = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')
    keyboard_row_width = 3
    response_msg = 'Выберите день недели'

    def dispatch(self):
        # set selected cinema in storage, this need for 'Info' handler
        bot_md.Storage.objects.update_or_create(
            account_id=self.message.from_user.id,
            key='selected_cinema',
            defaults={
                'account_id': self.message.from_user.id,
                'key': 'selected_cinema',
                'value': self.message.text
            }
        )

        super(Week, self).dispatch()

    @classmethod
    def get_week_days(cls):
        """ getter for __week_days attribute """
        current_weak_day = timezone.now().weekday()

        # making week days starting from current week day
        week_days = cls.__week_days[current_weak_day:] + cls.__week_days[:current_weak_day]

        return week_days

    def get_chunks_week_range(self):
        week_days = self.get_week_days()

        # adding 'info' and 'back' btn to the end of the range
        week_days += ('Инфо', EMOJI['back'])

        chunks_week_range = (
            tuple(week_days[i:i + self.keyboard_row_width])
            for i in range(0, len(week_days), self.keyboard_row_width)
        )

        return chunks_week_range

    def send_response(self):
        chunks_week_range = self.get_chunks_week_range()
        markup = self.get_markup(chunks_week_range)

        dag_afisha_bot.send_message(
            self.message.chat.id,
            self.response_msg,
            reply_markup=markup
        )


class FilmSchedule(Cinemas):
    model = bot_md.FilmSchedule

    def dispatch(self):
        # if selected cinema doesn't exist then send cinemas for selecting
        if not self.selected_cinema:
            return super(FilmSchedule, self).send_response()

        return self.send_response()

    def send_response(self):
        schedule = self.get_schedule()
        if not schedule.exists():
            schedule = self.parse_schedule_html()

        if not schedule:
            dag_afisha_bot.send_message(
                self.message.chat.id,
                'Расписания пока нет'
            )
            return None

        pretty_films_schedule = self.get_pretty_schedule(schedule)

        dag_afisha_bot.send_message(
            self.message.chat.id,
            pretty_films_schedule,
            parse_mode='HTML'
        )

    @property
    def selected_day(self):
        week_days = Week.get_week_days()

        offset = week_days.index(self.message.text)
        selected_day = timezone.now() + timezone.timedelta(days=offset)

        return selected_day

    def get_schedule(self):
        """ get schedule from db """
        selected_day = self.selected_day

        schedule = self.model.objects.filter(
            cinema=self.selected_cinema,
            date=selected_day
        )
        return schedule

    def get_schedule_html(self, selected_day):
        """ get schedule from remote site """

        day_str = selected_day.strftime('%Y-%m-%d')

        ajax_header = {
            'X-Requested-With': 'XMLHttpRequest'
        }

        response = requests.post(
            self.selected_cinema.schedule_url,
            data={'day': day_str},
            headers=ajax_header
        )
        schedule_html = response.content.decode('utf-8')

        return schedule_html.strip()

    def parse_schedule_html(self):
        """ parse schedule html and save in db """

        schedule_html = self.get_schedule_html(self.selected_day)

        if not schedule_html.startswith('<table'):
            return None

        table = BeautifulSoup(schedule_html, 'html.parser')

        films = table.find_all('tr')

        for film in films:
            name, info = film.find_all('td')
            name = name.find('a').string
            info_blocks = info.find_all('span', class_='times')
            for info in info_blocks:
                time = info.find('span').string
                format_tag = info.find('b', text='3D')
                film_format = getattr(format_tag, 'string', '2D')
                price = info.find_all('b')[-1].string
                price = price.split()[0].strip()

                self.model.objects.create(
                    cinema=self.selected_cinema,
                    name=name,
                    time=time,
                    film_format=film_format,
                    price=int(price),
                    date=self.selected_day
                )

        schedule = self.model.objects.filter(cinema=self.selected_cinema, date=self.selected_day)

        return schedule

    def get_pretty_schedule(self, schedule):
        """ Return readable format for films schedules """

        grouped_schedule = groupby(schedule, key=lambda x: x.name)

        pretty_film_schedules = []

        selected_week = '  <b>{}</b>  \n\n'.format(self.message.text)

        for schedule_group in grouped_schedule:
            film_name, films = schedule_group
            pretty_film_schedule = '<b>{}</b>  \n\n'.format(film_name)

            pretty_rows = [
                '|  {}  |  {} руб.  |  {}  '.format(
                    film.time, film.price, film.film_format
                ) for film in films
            ]
            pretty_film_schedule += '\n'.join(pretty_rows)

            pretty_film_schedules.append(pretty_film_schedule)

        return selected_week + '\n==============================\n\n'.join(pretty_film_schedules)


cinemas = bot_md.Cinema.objects.values_list('title', flat=True)

# mark all classes for handling messages
dag_afisha_bot.message_handler(commands=['start'])(Cinemas)
dag_afisha_bot.message_handler(regexp=EMOJI['back'])(Cinemas)

dag_afisha_bot.message_handler(regexp='Инфо')(Info)

dag_afisha_bot.message_handler(func=lambda message: message.text in cinemas)(Week)

dag_afisha_bot.message_handler(func=lambda message: message.text in Week.get_week_days())(FilmSchedule)


from telebot import apihelper

apihelper.proxy = {'https': 'socks5://207.180.212.121:1080'}

dag_afisha_bot.remove_webhook()

# dag_afisha_bot.polling()
