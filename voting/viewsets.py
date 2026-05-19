from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from .models import Voting, Nomination, Participant, Vote, WidgetNews, WidgetDailyPoll, WidgetTopVoting
from .serializers import (
    VotingSerializer, NominationSerializer, ParticipantSerializer, 
    VoteSerializer, WidgetNewsSerializer, WidgetDailyPollSerializer, WidgetTopVotingSerializer
)

class VotingViewSet(viewsets.ModelViewSet):
    queryset = Voting.objects.all()
    serializer_class = VotingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['title', 'start_date']
    search_fields = ['title', 'description']

    @action(methods=['GET'], detail=False)
    def active(self, request):
        active_votings = Voting.objects.filter(end_date__gte=now())
        serializer = self.get_serializer(active_votings, many=True)
        return Response(serializer.data)

    @action(methods=['POST'], detail=True)
    def close(self, request, pk=None):
        voting = self.get_object()
        voting.end_date = now()
        voting.save()
        return Response({'status': 'Голосование закрыто'})

    @action(methods=['GET'], detail=False)
    def mega_search(self, request):
        query = request.query_params.get('q', '')
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
        popular_list = Participant.objects.annotate(v_count=Count('votes')).order_by('-v_count')
        serializer = self.get_serializer(popular_list, many=True)
        return Response(serializer.data)

class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Vote.objects.filter(user=user)
        return Vote.objects.none()

class WidgetNewsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WidgetNews.objects.all()
    serializer_class = WidgetNewsSerializer

class WidgetDailyPollViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WidgetDailyPoll.objects.filter(is_active=True)
    serializer_class = WidgetDailyPollSerializer

class WidgetTopVotingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WidgetTopVoting.objects.all()
    serializer_class = WidgetTopVotingSerializer