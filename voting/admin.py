from django.contrib import admin
from django.utils.html import format_html # Для вывода безопасного HTML (Задание про @admin.display)
from django.urls import reverse # Для генерации URL-адресов по имени (Задание про reverse)
from django.http import HttpResponse
from import_export.admin import ExportMixin

# Для генерации PDF (Задание 5)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import Voting, Nomination, Participant, Vote, VotingParticipation
from .resources import VotingResource

# --- ACTIONS (Задание 5: Добавление действий на сайт администрирования) ---

@admin.action(description="Сделать выбранные голосования ПУБЛИЧНЫМИ")
def make_public(modeladmin, request, queryset):
    # queryset.update() — метод для массового обновления записей (Задание про update)
    updated = queryset.update(voting_type='public')
    modeladmin.message_user(request, f"Обновлено голосований: {updated}")

@admin.action(description="Сгенерировать PDF отчет")
def generate_pdf_report(modeladmin, request, queryset):
    # HttpResponse с типом pdf — говорит браузеру, что это не страница, а файл
    response = HttpResponse(content_type='application/pdf')
    # Content-Disposition — заставляет браузер скачать файл (Задание про PDF)
    response['Content-Disposition'] = 'attachment; filename="votings_report.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Votings Report")
    
    y = 750
    p.setFont("Helvetica", 12)
    # Цикл по queryset — отчет строится только по ВЫБРАННЫМ объектам (Задание про queryset)
    for obj in queryset:
        # get_voting_type_display() — метод Django для получения человеческого названия из choices
        p.drawString(100, y, f"- {obj.title} (Тип: {obj.get_voting_type_display()})")
        y -= 20
        if y < 50: 
            p.showPage()
            y = 800
            
    p.showPage()
    p.save()
    return response

# --- ADMIN CLASSES ---

# Inlines позволяют редактировать связанные объекты на одной странице (Задание про Inlines)
class NominationInline(admin.TabularInline):
    model = Nomination
    extra = 0

class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 1

@admin.register(Voting)
class VotingAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = VotingResource
    # list_display — колонки в списке (Задание про list_display)
    list_display = ("title", "voting_type", "start_date", "end_date", "display_status")
    # list_display_links — какие колонки сделать ссылками на редактирование
    list_display_links = ("title", "display_status")
    # list_filter — фильтры справа (Задание про list_filter)
    list_filter = ("voting_type", "start_date", "end_date")
    inlines = [NominationInline]
    # search_fields — поле поиска (Задание про search_fields)
    search_fields = ("title",)
    # date_hierarchy — навигация по датам сверху (Задание про date_hierarchy)
    date_hierarchy = 'start_date'
    # readonly_fields — поля только для чтения (Задание про readonly_fields)
    readonly_fields = ("created_at", "updated_at")
    
    # Регистрация созданных выше действий
    actions = [make_public, generate_pdf_report]

    # Собственный метод внутри list_display с использованием HTML (Задание про @admin.display)
    @admin.display(description="Статус") # Замена short_description в новых версиях
    def display_status(self, obj):
        if obj.is_active:
            return format_html('<b style="color: green;">Активно</b>')
        return format_html('<b style="color: red;">Завершено</b>')

@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ('title', 'voting')
    # Использование __ для фильтрации по полю связанной таблицы (Задание про __)
    list_filter = ('voting__title',)
    inlines = [ParticipantInline]
    search_fields = ('title', 'voting__title')

@admin.register(Participant)
class ParticipantAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("name", "link_to_nomination", "votes_count_display", "has_avatar")
    # raw_id_fields — заменяет выпадающий список на ввод ID (Задание про raw_id_fields)
    raw_id_fields = ("nomination",) 
    search_fields = ("name", "nomination__title")

    # Метод для отображения иконки (boolean=True заменяет текст на галочку)
    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = "Фото"

    # Использование reverse для генерации ссылки на другой объект в админке
    def link_to_nomination(self, obj):
        link = reverse("admin:voting_nomination_change", args=[obj.nomination.id])
        return format_html('<a href="{}">{}</a>', link, obj.nomination.title)
    link_to_nomination.short_description = "Номинация"

    # Метод агрегирования (подсчет голосов "на лету") (Задание про агрегацию/count)
    @admin.display(description="Голосов")
    def votes_count_display(self, obj):
        # .count() — метод QuerySet для подсчета записей
        return obj.votes.count()

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "participant", "voted_at")
    raw_id_fields = ("user", "participant")
    # Фильтрация через две таблицы сразу (Голосование -> Номинация -> Участник)
    list_filter = ("participant__nomination__voting", "voted_at")
    date_hierarchy = 'voted_at'

admin.site.register(VotingParticipation)