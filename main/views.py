import logging
import os
from django.conf import settings
import telebot
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import generic as gc
from django import http
from bot.views import dag_afisha_bot, dag_afisha_logger


@method_decorator(csrf_exempt, name='dispatch')
class DagAfishaWebhookHandler(gc.View):

    def get(self, request):
        """ set web hook """
        dag_afisha_bot.remove_webhook()

        webhook_url = request.build_absolute_uri(request.path)
        dag_afisha_logger.info('webhook_url: ' + webhook_url)

        dag_afisha_bot.set_webhook(url=webhook_url)

        return http.HttpResponse('Success webhook set')

    def post(self, request):
        """ handle sent updates from telegram """

        json_update = request.read()

        # convert byte str to unicode str
        json_update = json_update.decode('utf-8')

        dag_afisha_logger.info('==========================================')
        dag_afisha_logger.info('dag_fisha: '+json_update)

        update = telebot.types.Update.de_json(json_update)

        dag_afisha_bot.process_new_messages([update.message])

        return http.HttpResponse()

