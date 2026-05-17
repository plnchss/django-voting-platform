from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from .models import Voting, Nomination, Participant, Vote
from .serializers import VotingSerializer, NominationSerializer, ParticipantSerializer, VoteSerializer

# ModelViewSet автоматически обрабатывает базовый CRUD (создание, чтение, обновление, удаление)
class VotingViewSet(viewsets.ModelViewSet):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    
    # Настройка фильтрации (DjangoFilterBackend — точные поля, SearchFilter — текстовый поиск)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['title', 'start_date'] # Точное совпадение (Задание 12)
    search_fields = ['title', 'description']    # Поиск по подстроке (Задание 12)

    # @action создает дополнительные маршруты в API. detail=False означает путь /active/
    @action(methods=['GET'], detail=False)
    def active(self, request):
        """Возвращает только те голосования, дата окончания которых еще не наступила"""
        active_votings = Voting.objects.filter(end_date__gte=now())
        serializer = self.get_serializer(active_votings, many=True)
        return Response(serializer.data)

    # detail=True означает работу с конкретным объектом по ID: /<id>/close/
    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        """Метод для принудительного закрытия голосования текущим моментом"""
        voting = self.get_object() # Автоматически находит объект по ID
        voting.end_date = now()
        voting.save()
        return Response({'status': 'Голосование закрыто'})

    # Использование Q-объектов для сложных запросов (Задание 6 - ТРЕБОВАНИЕ НА "ХОРОШО")
    @action(methods=['GET'], detail=False)
    def mega_search(self, request):
        query = request.query_params.get('q', '')
        # Логика: (A ИЛИ B) И НЕ C. icontains — поиск без учета регистра
        results = Voting.objects.filter(
            (Q(title__icontains=query) | Q(description__icontains=query)) & 
            ~Q(title__icontains='архив')
        )
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)

class NominationViewSet(viewsets.ModelViewSet):
    queryset = Nomination.objects.all()
    serializer_class = NominationSerializer

class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all()
    serializer_class = ParticipantSerializer

    @action(methods=['GET'], detail=False)
    def popular(self, request):
        from django.db.models import Count
        popular_list = Participant.objects.annotate(v_count=Count('votes')).order_by('-v_count')
        serializer = self.get_serializer(popular_list, many=True)
        return Response(serializer.data)

class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    def get_queryset(self):
        """Ограничивает список голосов так, чтобы пользователь видел только свои голоса"""
        user = self.request.user
        if user.is_authenticated:
            return Vote.objects.filter(user=user)
        return Vote.objects.none() # Анонимам не показываем ничего