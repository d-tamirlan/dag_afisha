import os
from django.conf import settings
from itertools import groupby
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import telebot
import requests
import logging
from chatbase import Message
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


# class BotAnalytic:
#     message = ''
#     response_msg = ''
#
#     def send_bot_analytics(self):
#         user = self.message.from_user
#         user_id = user.username or user.id
#
#         analytics_data = {
#             'api_key': settings.CHATBASE_API_KEY,
#             'type': 'user',
#             'user_id': user_id,
#             'platform': 'Telegram',
#             'message': self.message.text,
#             'not_handled': False,
#             'intent': 'Старт',
#             'version': '0.1'
#         }
#         Message(**analytics_data).send()
#
#         del analytics_data['not_handled']
#         analytics_data['type'] = 'agent'
#         analytics_data['message'] = self.response_msg
#
#         Message(**analytics_data).send()


class Cinemas:
    model = bot_md.Cinema
    group_by = 3
    response_msg = 'Выберите кинотеатр'
    message = ''

    def __init__(self):
        dag_afisha_bot.message_handler(commands=['start'])(self.send_cinemas)
        dag_afisha_bot.message_handler(regexp=EMOJI['back'])(self.send_cinemas)

        dag_afisha_bot.message_handler(regexp='Инфо')(self.send_info)

    def get_markup(self):
        markup = telebot.types.ReplyKeyboardMarkup(row_width=self.group_by, resize_keyboard=True)
        for cinema_group in self.group_cinemas():
            cinema_group_btns = (
                telebot.types.KeyboardButton(cinema)
                for cinema in cinema_group
            )
            markup.add(*cinema_group_btns)

        return markup

    def get_cinemas(self):
        cinemas = self.model.objects.values_list('title', flat=True)
        return cinemas

    def group_cinemas(self):
        cinemas = self.get_cinemas()
        grouped_cinemas = [
            tuple(cinemas[i:i + self.group_by])
            for i in range(0, len(cinemas), self.group_by)
        ]

        # dag_afisha_logger.info('grouped_cinemas: ')
        # dag_afisha_logger.info(grouped_cinemas)

        return grouped_cinemas

    def send_info(self, message):
        try:
            selected_cinema = bot_md.Storage.objects.get(
                account_id=message.from_user.id,
                key='selected_cinema',
            )
        except ObjectDoesNotExist:
            return self.send_cinemas(message)

        cinema = self.model.objects.get(title=selected_cinema.value)

        dag_afisha_bot.send_message(
            message.chat.id,
            cinema.description,
        )

    def send_cinemas(self, message):
        try:
            self.message = message
            markup = self.get_markup()

            dag_afisha_bot.send_message(
                message.chat.id,
                self.response_msg,
                reply_markup=markup
            )
        except Exception as e:
            dag_afisha_logger.info('-*-send_cinemas exception-*-: '+str(e))


class Weeks:
    model = bot_md.Cinema
    week_days = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')
    group_by = 3
    message = {}
    response_msg = 'Выберите день недели'

    def __init__(self):
        cinemas = Cinemas().get_cinemas()
        dag_afisha_bot.message_handler(func=lambda message: message.text in cinemas)(self.dispatch)

    def dispatch(self, message):
        try:
            self.message = message
            self.set_storage_data()
            self.send_week_range()
        except Exception as e:
            dag_afisha_logger.info('-*-Weeks Exception-*-: '+str(e))

    def set_storage_data(self):
        selected_cinema = bot_md.Storage.objects.filter(
            account_id=self.message.from_user.id,
            key='selected_cinema',
        )
        if selected_cinema.exists():
            selected_cinema.update(value=self.message.text)
        else:
            bot_md.Storage.objects.create(
                account_id=self.message.from_user.id,
                key='selected_cinema',
                value=self.message.text
            )

    def get_week_range(self):
        current_weak_day = timezone.now().weekday()
        weeks_range = self.week_days[current_weak_day:] + self.week_days[:current_weak_day]
        # dag_afisha_logger.info('weeks_range:' + str(weeks_range))
        return weeks_range

    def group_week_range(self):
        week_range = self.get_week_range() + ('Инфо', EMOJI['back'])
        grouped_week_range = [
            tuple(week_range[i:i + self.group_by])
            for i in range(0, len(week_range), self.group_by)
        ]
        # dag_afisha_logger.info('grouped_week_range:' + str(grouped_week_range))

        return grouped_week_range

    def get_markup(self):
        markup = telebot.types.ReplyKeyboardMarkup(row_width=self.group_by, resize_keyboard=True)
        for weak_chunk in self.group_week_range():
            weak_chunk_btns = (
                telebot.types.KeyboardButton(weak)
                for weak in weak_chunk
            )
            markup.add(*weak_chunk_btns)

        return markup

    def send_week_range(self):
        markup = self.get_markup()

        dag_afisha_bot.send_message(
            self.message.chat.id,
            self.response_msg,
            reply_markup=markup
        )
        # film_schedule = FilmSchedule(message.text, self.get_week_range())
        # dag_afisha_bot.register_next_step_handler(message, film_schedule.send_schedule)


class FilmSchedule:
    model = bot_md.FilmSchedule
    selected_cinema = ''
    week_days = ()
    message = {}

    def __init__(self, week_days):
        # dag_afisha_logger.info('selected_cinema: ' + selected_cinema)
        # cinema = bot_md.Cinema.objects.get(title=selected_cinema)
        # self.selected_cinema = cinema
        self.week_days = week_days
        # dag_afisha_logger.info('FilmSchedule init Exception: '+ str(e))

        dag_afisha_bot.message_handler(func=lambda message: message.text in week_days)(self.dispatch)

    def dispatch(self, message):
        try:
            self.message = message
            if self.init_storage_data() is False:
                return False

            self.send_schedule()
        except Exception as e:
            dag_afisha_logger.info('-*-FilmSchedule dispatch Exception-*-: '+str(e))

    def init_storage_data(self):
        try:
            last_selected_cinema = bot_md.Storage.objects.get(
                account_id=self.message.from_user.id,
                key='selected_cinema'
            )
        except ObjectDoesNotExist:
            Cinemas().send_cinemas(self.message)
            return False

        self.selected_cinema = bot_md.Cinema.objects.get(title=last_selected_cinema.value)

    def get_selected_day(self, day):
        offset = self.week_days.index(day)
        selected_day = timezone.now() + timezone.timedelta(days=offset)
        return selected_day

    def get_schedule(self, selected_day):
        """ get schedule from db """
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

    def parse_schedule_html(self, selected_day):
        """ parse schedule html and save in db """

        schedule_html = self.get_schedule_html(selected_day)

        if not schedule_html.startswith('<table'):
            return False

        table = BeautifulSoup(schedule_html, 'html.parser')

        films = table.find_all('tr')

        for film in films:
            name, info = film.find_all('td')
            name = name.find('a').string
            info_blocks = info.find_all('span', class_='times')
            for info in info_blocks:
                time = info.find('span').string
                format_tag = info.find('b', text='3D')
                film_format = format_tag.string if format_tag else '2D'
                price = info.find_all('b')[-1].string
                price = price.split()[0].strip()

                self.model.objects.create(
                    cinema=self.selected_cinema,
                    name=name,
                    time=time,
                    film_format=film_format,
                    price=int(price),
                    date=selected_day
                )

        schedule = self.model.objects.filter(cinema=self.selected_cinema, date=selected_day)

        return schedule

    def group_schedule(self, schedule):
        grouped_schedule = groupby(schedule, key=lambda x: x.name)
        return grouped_schedule

    def get_pretty_texts(self, schedule):
        grouped_schedule = self.group_schedule(schedule)
        pretty_texts = []
        for schedule_group in grouped_schedule:
            film_name, films = schedule_group
            pretty_text = '  <b>{}</b>  \n\n'.format(film_name)

            for film in films:
                pretty_row = '|  {}  |  {} руб.  |  {}  \n'.format(
                    film.time, film.price, film.film_format
                )
                pretty_text += pretty_row

            pretty_texts.append(pretty_text)

        return pretty_texts

    def send_schedule(self):
        selected_day = self.get_selected_day(self.message.text)
        schedule = self.get_schedule(selected_day)
        if not schedule.exists():
            schedule = self.parse_schedule_html(selected_day)

        if schedule is False:
            dag_afisha_bot.send_message(
                self.message.chat.id,
                'Расписания пока нет'
            )
        else:
            for pretty_text in self.get_pretty_texts(schedule):
                dag_afisha_bot.send_message(
                    self.message.chat.id,
                    pretty_text,
                    parse_mode='HTML'
                )

            # dag_afisha_bot.register_next_step_handler(message, self.send_schedule)

Cinemas()
FilmSchedule(Weeks().get_week_range())

# @dag_afisha_bot.message_handler(commands=['start'])
# def echo_bot(message):
#     dag_afisha_bot.send_message(
#         message.chat.id,
#         'Здравствуйте, выберите кинотеатр',
#     )
