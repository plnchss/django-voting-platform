from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponse
from import_export.admin import ExportMixin
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import (
    Voting, Nomination, Participant, Vote, VotingParticipation,
    WidgetNews, WidgetDailyPoll, WidgetDailyPollOption, WidgetTopVoting
)
from .resources import VotingResource


@admin.action(description="Сделать выбранные голосования ПУБЛИЧНЫМИ")
def make_public(modeladmin, request, queryset):
    updated = queryset.update(voting_type='public')
    modeladmin.message_user(request, f"Обновлено голосований: {updated}")


@admin.action(description="Сгенерировать PDF отчет")
def generate_pdf_report(modeladmin, request, queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="votings_report.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "Votings Report")
    
    y = 750
    p.setFont("Helvetica", 12)
    for obj in queryset:
        p.drawString(100, y, f"- {obj.title} (Тип: {obj.get_voting_type_display()})")
        y -= 20
        if y < 50: 
            p.showPage()
            y = 800
            
    p.showPage()
    p.save()
    return response


class NominationInline(admin.TabularInline):
    model = Nomination
    extra = 0


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 1


class WidgetDailyPollOptionInline(admin.TabularInline):
    model = WidgetDailyPollOption
    extra = 2


@admin.register(Voting)
class VotingAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = VotingResource
    list_display = ("title", "voting_type", "start_date", "end_date", "display_status")
    list_display_links = ("title", "display_status")
    list_filter = ("voting_type", "start_date", "end_date")
    inlines = [NominationInline]
    search_fields = ("title",)
    date_hierarchy = 'start_date'
    readonly_fields = ("created_at", "updated_at")
    actions = [make_public, generate_pdf_report]

    @admin.display(description="Статус")
    def display_status(self, obj):
        if obj.is_active():
            return format_html('<b style="color: green;">Активно</b>')
        return format_html('<b style="color: red;">Завершено</b>')


@admin.register(Nomination)
class NominationAdmin(admin.ModelAdmin):
    list_display = ('title', 'voting')
    list_filter = ('voting__title',)
    inlines = [ParticipantInline]
    search_fields = ('title', 'voting__title')


@admin.register(Participant)
class ParticipantAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ("name", "link_to_nomination", "votes_count_display", "has_avatar")
    raw_id_fields = ("nomination",) 
    search_fields = ("name", "nomination__title")

    def has_avatar(self, obj):
        return bool(obj.avatar)
    has_avatar.boolean = True
    has_avatar.short_description = "Фото"

    def link_to_nomination(self, obj):
        link = reverse("admin:voting_nomination_change", args=[obj.nomination.id])
        return format_html('<a href="{}">{}</a>', link, obj.nomination.title)
    link_to_nomination.short_description = "Номинация"

    @admin.display(description="Голосов")
    def votes_count_display(self, obj):
        return obj.votes.count()


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "participant", "voted_at")
    raw_id_fields = ("user", "participant")
    list_filter = ("participant__nomination__voting", "voted_at")
    date_hierarchy = 'voted_at'
    readonly_fields = ('voted_at',)


@admin.register(WidgetNews)
class WidgetNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_important', 'created_at')
    list_filter = ('is_important', 'created_at')
    search_fields = ('title', 'content')


@admin.register(WidgetDailyPoll)
class WidgetDailyPollAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('question',)
    inlines = [WidgetDailyPollOptionInline]


@admin.register(WidgetTopVoting)
class WidgetTopVotingAdmin(admin.ModelAdmin):
    list_display = ('voting', 'views_count', 'clicks_count')
    raw_id_fields = ('voting',)
    search_fields = ('voting__title',)


admin.site.register(VotingParticipation)