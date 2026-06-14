from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.timezone import now
from simple_history.models import HistoricalRecords


class VotingManager(models.Manager):
    def active(self):
        return self.filter(start_date__lte=now(), end_date__gte=now())

    def public(self):
        return self.filter(voting_type='public')


class Voting(models.Model):
    VOTING_TYPES = [
        ('public', 'Публичное'),
        ('invite_only', 'По ссылке'),
        ('private', 'Закрытое (Черновик)'),
    ]
    
    title = models.CharField("Название голосования", max_length=255)
    description = models.TextField("Описание", blank=True)
    start_date = models.DateTimeField("Дата начала")
    end_date = models.DateTimeField("Дата окончания")
    voting_type = models.CharField("Тип", max_length=15, choices=VOTING_TYPES, default='public')
    rules_file = models.FileField("Приложение к голосованию", upload_to='rules/%Y/%m/', blank=True, null=True)
    external_link = models.URLField("Внешняя ссылка", max_length=200, blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)
    
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="owned_votings",
        verbose_name="Организатор"
    )

    participants_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='VotingParticipation',
        related_name='joined_votings',
        verbose_name="Участники-пользователи"
    )

    objects = models.Manager()
    active_objects = VotingManager()
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Голосование" 
        verbose_name_plural = "Голосования"
        ordering = ["-created_at"] 

    def __str__(self):
        return self.title

    def is_active(self):
        return self.start_date <= now() <= self.end_date
    
    is_active.boolean = True
    is_active.short_description = "Активно"

    def is_finished(self):
        return now() > self.end_date

    @property
    def days_left(self):
        if self.end_date and self.end_date > now():
            delta = self.end_date - now()
            return delta.days
        return 0

    def get_absolute_url(self):
        return reverse('voting_detail', args=[str(self.id)])

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError("Дата начала должна быть раньше даты окончания")


class VotingParticipation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="participations",
        verbose_name="Пользователь"
    )
    voting = models.ForeignKey(
        Voting, 
        on_delete=models.CASCADE, 
        related_name="participations",
        verbose_name="Голосование"
    )
    date_joined = models.DateTimeField("Дата присоединения", auto_now_add=True)

    class Meta:
        unique_together = ('user', 'voting')
        verbose_name = "Участие в голосовании"
        verbose_name_plural = "Участия в голосованиях"

    def __str__(self):
        return f"{self.user.username} — {self.voting.title}"


class Nomination(models.Model):
    voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name="nominations", verbose_name="Голосование")
    title = models.CharField("Название номинации", max_length=255)
    description = models.TextField("Описание", blank=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ("voting", "title")
        verbose_name = "Номинация"
        verbose_name_plural = "Номинации"

    def __str__(self):
        return f"{self.title} ({self.voting.title})"


class Participant(models.Model):
    nomination = models.ForeignKey(Nomination, on_delete=models.CASCADE, related_name="participants", verbose_name="Номинация")
    name = models.CharField("Имя участника", max_length=255)
    description = models.TextField("Описание", blank=True)
    avatar = models.ImageField("Аватар", upload_to="participants/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField("Дата регистрации", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Участник"
        verbose_name_plural = "Участники"

    def __str__(self):
        return self.name


class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes", verbose_name="Пользователь")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="votes", verbose_name="За кого голос")
    voted_at = models.DateTimeField("Дата и время", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ("user", "participant")
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"

    def __str__(self):
        return f"Голос от {self.user.username} за {self.participant.name}"

class WidgetNews(models.Model):
    """Виджет 1: Важные новости и объявления на главной"""
    title = models.CharField("Заголовок новости", max_length=255)
    content = models.TextField("Текст новости")
    is_important = models.BooleanField("Закрепленная/Важная", default=False)
    created_at = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        verbose_name = "Виджет: Новость"
        verbose_name_plural = "Виджет 1: Новости и Объявления"
        ordering = ["-is_important", "-created_at"]

    def __str__(self):
        return self.title


class WidgetDailyPoll(models.Model):
    """Виджет 2: Быстрый опрос дня (однокликовый)"""
    question = models.CharField("Вопрос дня", max_length=255)
    is_active = models.BooleanField("Активен (Отображается на главной)", default=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Виджет: Быстрый опрос"
        verbose_name_plural = "Виджет 2: Быстрые опросы"

    def __str__(self):
        return self.question


class WidgetDailyPollOption(models.Model):
    """Варианты ответов для быстрого опроса со счетчиком голосов"""
    poll = models.ForeignKey(WidgetDailyPoll, on_delete=models.CASCADE, related_name="options", verbose_name="Опрос")
    text = models.CharField("Вариант ответа", max_length=100)
    votes_count = models.PositiveIntegerField("Количество голосов", default=0)

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"

    def __str__(self):
        return f"{self.text} (Голосов: {self.votes_count})"


class WidgetTopVoting(models.Model):
    """Виджет 3: Топ активных голосований по просмотрам/кликам (Аналитика)"""
    voting = models.OneToOneField(Voting, on_delete=models.CASCADE, related_name="analytics", verbose_name="Голосование")
    views_count = models.PositiveIntegerField("Количество просмотров", default=0)
    clicks_count = models.PositiveIntegerField("Количество кликов по кнопкам", default=0)

    class Meta:
        verbose_name = "Виджет: Аналитика голосования"
        verbose_name_plural = "Виджет 3: Топ популярных голосований"
        ordering = ["-views_count", "-clicks_count"]

    def __str__(self):
        return f"Аналитика для: {self.voting.title}"