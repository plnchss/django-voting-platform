# voting/filters.py
from django_filters import rest_framework as filters
from django.utils.timezone import now
from .models import Voting, Nomination, Participant, Vote

# ---------------- Voting Filter (Фильтрация голосований) ----------------
class VotingFilter(filters.FilterSet):
    # BooleanFilter — фильтр-галочка (да/нет)
    active = filters.BooleanFilter(method='filter_active') # Вызывает кастомный метод
    expired = filters.BooleanFilter(method='filter_expired') 
    # CharFilter с icontains — поиск по части названия без учета регистра
    title = filters.CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = Voting
        # Поля, по которым можно фильтровать напрямую (равенство)
        fields = ['start_date', 'end_date', 'title']

    # Логика фильтрации "Активных": старт уже был, а конец еще не наступил
    def filter_active(self, queryset, name, value):
        if value:
            return queryset.filter(start_date__lte=now(), end_date__gte=now())
        return queryset

    # Логика "Просроченных": текущая дата больше даты окончания
    def filter_expired(self, queryset, name, value):
        if value:
            return queryset.filter(end_date__lt=now())
        return queryset

# ---------------- Nomination Filter (Фильтрация номинаций) ----------------
class NominationFilter(filters.FilterSet):
    # Поиск по названию связанного голосования (использование __ для доступа к полю voting)
    voting_title = filters.CharFilter(field_name='voting__title', lookup_expr='icontains')
    min_participants = filters.NumberFilter(method='filter_min_participants')

    class Meta:
        model = Nomination
        fields = ['voting', 'title']

    # Продвинутая фильтрация с использованием агрегации (annotate)
    def filter_min_participants(self, queryset, name, value):
        # Считаем количество участников и оставляем только те номинации, где их >= value
        return queryset.annotate(num=filters.Count('participants')).filter(num__gte=value)

# ---------------- Participant Filter (Фильтрация участников) ----------------
class ParticipantFilter(filters.FilterSet):
    # Фильтр по названию номинации (через связь ForeignKey)
    nomination_title = filters.CharFilter(field_name='nomination__title', lookup_expr='icontains')
    min_votes = filters.NumberFilter(method='filter_min_votes')

    class Meta:
        model = Participant
        fields = ['nomination', 'name']

    # Фильтр участников по минимальному количеству полученных голосов
    def filter_min_votes(self, queryset, name, value):
        return queryset.annotate(num=filters.Count('votes')).filter(num__gte=value)

# ---------------- Vote Filter (Фильтрация голосов) ----------------
class VoteFilter(filters.FilterSet):
    # Глубокая фильтрация через две таблицы: Голос -> Участник -> Номинация
    nomination = filters.NumberFilter(field_name='participant__nomination')
    # Глубокая фильтрация через три таблицы: Голос -> Участник -> Номинация -> Голосование
    voting = filters.NumberFilter(field_name='participant__nomination__voting')

    class Meta:
        model = Vote
        fields = ['user', 'participant', 'nomination', 'voting']