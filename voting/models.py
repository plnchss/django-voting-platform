from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError # Для создания собственных ошибок (Задание про валидацию)
from django.utils.timezone import now # Текущее время с учетом часового пояса
from django.urls import reverse # Для генерации ссылок (Задание про reverse/get_absolute_url)
from simple_history.models import HistoricalRecords # Для ведения логов изменений объекта

# 1. КАСТОМНЫЙ МЕНЕДЖЕР (Задание про Использование собственного модельного менеджера)
class VotingManager(models.Manager):
    """Позволяет делать запросы типа Voting.active_objects.active()"""
    def active(self):
        # Фильтруем голосования, которые идут прямо сейчас
        return self.filter(start_date__lte=now(), end_date__gte=now())

    def public(self):
        # Фильтруем только публичные записи
        return self.filter(voting_type='public')

# 2. МОДЕЛЬ ГОЛОСОВАНИЯ
class Voting(models.Model):
    VOTING_TYPES = [
        ('public', 'Публичное'),
        ('private', 'Закрытое'),
    ]
    
    title = models.CharField("Название голосования", max_length=255)
    description = models.TextField("Описание", blank=True)
    start_date = models.DateTimeField("Дата начала")
    end_date = models.DateTimeField("Дата окончания")
    voting_type = models.CharField("Тип", max_length=10, choices=VOTING_TYPES, default='public')
    rules_file = models.FileField("Файл с правилами", upload_to='rules/%Y/%m/', blank=True, null=True)
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

    # ManyToManyField через промежуточную таблицу (Задание про through)
    participants_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='VotingParticipation', # Указываем класс таблицы-посредника
        related_name='joined_votings',
        verbose_name="Участники-пользователи"
    )

    objects = models.Manager() # Стандартный менеджер
    active_objects = VotingManager() # кастомный менеджер
    history = HistoricalRecords() # Запись истории изменений

    class Meta:
        verbose_name = "Голосование" 
        verbose_name_plural = "Голосования"
        ordering = ["-created_at"] 

    def __str__(self):
        # Метод определяет, как объект выглядит в виде строки (Задание про __str__)
        return self.title

    # --- МЕТОДЫ ДЛЯ АДМИНКИ И ВЬЮХ ---
    
    def is_active(self):
        """Проверяет, активно ли голосование в данный момент"""
        return self.start_date <= now() <= self.end_date
    
    is_active.boolean = True # Отображает в админке галочку вместо True/False
    is_active.short_description = "Активно"

    def is_finished(self):
        return now() > self.end_date

    # get_absolute_url — стандарт Django для получения ссылки на объект (Задание про get_absolute_url)
    def get_absolute_url(self):
        return reverse('voting_detail', args=[str(self.id)])

    # clean — метод для сложной валидации (Задание про проверку дат)
    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                # Генерируем ошибку, если дата начала позже конца
                raise ValidationError("Дата начала должна быть раньше даты окончания")

# 3. ПРОМЕЖУТОЧНАЯ ТАБЛИЦА (Задание про models.ManyToManyField с параметром through)
class VotingParticipation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="participations", # Исправлено: добавлен related_name
        verbose_name="Пользователь"
    )
    voting = models.ForeignKey(
        Voting, 
        on_delete=models.CASCADE, 
        related_name="participations", # Исправлено: добавлен related_name
        verbose_name="Голосование"
    )
    date_joined = models.DateTimeField("Дата присоединения", auto_now_add=True)

    class Meta:
        unique_together = ('user', 'voting') # Запрет на повторное вступление одного юзера в то же голосование
        verbose_name = "Участие в голосовании"
        verbose_name_plural = "Участия в голосованиях"

    # Исправлено: добавлен метод __str__, убирающий ошибку "object (2)" из админки
    def __str__(self):
        return f"{self.user.username} — {self.voting.title}"

# 4. НОМИНАЦИИ
class Nomination(models.Model):
    # on_delete=models.CASCADE — удалит номинации при удалении голосования
    voting = models.ForeignKey(Voting, on_delete=models.CASCADE, related_name="nominations", verbose_name="Голосование")
    title = models.CharField("Название номинации", max_length=255)
    description = models.TextField("Описание", blank=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ("voting", "title") # Уникальность названия внутри ОДНОГО голосования
        verbose_name = "Nomination"
        verbose_name_plural = "Номинации"

    def __str__(self):
        return f"{self.title} ({self.voting.title})"

# 5. УЧАСТНИКИ
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

# 6. ГОЛОСА
class Vote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="votes", verbose_name="Пользователь")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="votes", verbose_name="За кого голос")
    voted_at = models.DateTimeField("Дата и время", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        # Один юзер — один голос за ОДНОГО участника (защита от накрутки)
        unique_together = ("user", "participant")
        verbose_name = "Голос"
        verbose_name_plural = "Голоса"

    def __str__(self):
        return f"Голос от {self.user.username} за {self.participant.name}"