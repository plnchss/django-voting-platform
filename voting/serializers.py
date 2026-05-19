from rest_framework import serializers
from datetime import timedelta
from .models import (
    Voting, Nomination, Participant, Vote, 
    WidgetNews, WidgetDailyPoll, WidgetDailyPollOption, WidgetTopVoting
)

class VotingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Voting
        fields = '__all__'

    def validate(self, attrs):
        start = attrs.get('start_date')
        end = attrs.get('end_date')
        if start and end and (end - start) < timedelta(hours=1):
            raise serializers.ValidationError("Голосование должно длиться минимум 1 час.")
        return attrs

class NominationSerializer(serializers.ModelSerializer):
    participants_count = serializers.SerializerMethodField()

    class Meta:
        model = Nomination
        fields = ["id", "title", "description", "voting", "participants_count"]

    def get_participants_count(self, obj):
        return obj.participants.count()

class ParticipantSerializer(serializers.ModelSerializer):
    votes_count = serializers.ReadOnlyField(source="votes.count")

    class Meta:
        model = Participant
        fields = ["id", "name", "description", "nomination", "votes_count"]

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ["id", "user", "participant", "voted_at"]
        read_only_fields = ["user", "voted_at"]

    def validate(self, attrs):
        user = self.context["request"].user
        participant = attrs["participant"]
        voting = participant.nomination.voting

        if Vote.objects.filter(user=user, participant__nomination=participant.nomination).exists():
            raise serializers.ValidationError("Вы уже голосовали в этой номинации")
        
        if not voting.is_active():
            raise serializers.ValidationError("Голосование завершено или еще не началось")
            
        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

class WidgetNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetNews
        fields = '__all__'

class WidgetDailyPollOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetDailyPollOption
        fields = ['id', 'text', 'votes_count']

class WidgetDailyPollSerializer(serializers.ModelSerializer):
    options = WidgetDailyPollOptionSerializer(many=True, read_only=True)

    class Meta:
        model = WidgetDailyPoll
        fields = ['id', 'question', 'options']

class WidgetTopVotingSerializer(serializers.ModelSerializer):
    voting_title = serializers.CharField(source='voting.title', read_only=True)

    class Meta:
        model = WidgetTopVoting
        fields = ['id', 'voting_title', 'views_count', 'clicks_count']