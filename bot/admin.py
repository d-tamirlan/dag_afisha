from django.contrib import admin
from . import models as md


@admin.register(md.TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    pass


@admin.register(md.Cinema)
class CinemaAdmin(admin.ModelAdmin):
    pass


@admin.register(md.FilmSchedule)
class FilmScheduleAdmin(admin.ModelAdmin):
    pass


@admin.register(md.Storage)
class StorageAdmin(admin.ModelAdmin):
    pass
