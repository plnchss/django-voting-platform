from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, get_user_model
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.contrib import messages

from .models import Voting, Participant, Vote, VotingParticipation
from .forms import VotingForm

def main_page(request):
    current_time = now()
    
    stats = {
        'total_users': get_user_model().objects.count(),
        'total_votings': Voting.objects.count(),
        'total_votes': Vote.objects.count(),
    }

    base_qs = Voting.objects.filter(
        start_date__lte=current_time, 
        end_date__gte=current_time
    ).filter(Q(voting_type='public') | Q(voting_type='invite_only'))

    popular_votings = base_qs.annotate(
        total_votes=Count('nominations__participants__votes')
    ).order_by('-total_votes')[:3]

    top_participants = Participant.objects.filter(
        name__isnull=False
    ).exclude(name__exact='').annotate(
        votes_count=Count('votes')
    ).order_by('-votes_count')[:3]

    recent_votes = Vote.objects.select_related(
        'user', 
        'participant__nomination__voting'
    ).order_by('-id')[:3]

    return render(request, 'voting/main.html', {
        'stats': stats,
        'popular_votings': popular_votings,
        'top_participants': top_participants,
        'recent_votes': recent_votes,
    })


def index(request):
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'all')
    sort = request.GET.get('sort', 'new')
    
    # Базовая фильтрация доступа
    if request.user.is_authenticated:
        votings_qs = Voting.objects.filter(Q(voting_type='public') | Q(owner=request.user))
    else:
        votings_qs = Voting.objects.filter(voting_type='public')

    # Поиск
    if query:
        votings_qs = votings_qs.filter(Q(title__icontains=query) | Q(description__icontains=query))

    # Фильтр по статусу (предполагаем, что is_active() — это метод модели или свойство)
    current_time = now()
    if status == 'active':
        votings_qs = votings_qs.filter(start_date__lte=current_time, end_date__gte=current_time)
    elif status == 'finished':
        votings_qs = votings_qs.filter(end_date__lt=current_time)

    if sort == 'old':
        votings_qs = votings_qs.order_by("created_at")
    else:
        votings_qs = votings_qs.order_by("-created_at")

    votings_list = votings_qs.select_related('owner').prefetch_related('nominations')
    
    paginator = Paginator(votings_list, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'voting/index.html', {
        'page_obj': page_obj,
        'query': query,
        'current_status': status,
        'current_sort': sort,
        'current_time': current_time
    })


def voting_detail(request, voting_id):
    voting = get_object_or_404(
        Voting.objects.select_related('owner').prefetch_related('nominations__participants'), 
        pk=voting_id
    )
    
    # ИСПРАВЛЕНИЕ: Обработка голосования здесь
    if request.method == 'POST' and request.user.is_authenticated and voting.is_active():
        for nomination in voting.nominations.all():
            participant_id = request.POST.get(f'nomination_{nomination.id}')
            if participant_id:
                # Удаляем старый голос в этой конкретной номинации
                Vote.objects.filter(user=request.user, participant__nomination=nomination).delete()
                # Создаем новый
                participant = get_object_or_404(Participant, pk=participant_id)
                Vote.objects.create(user=request.user, participant=participant)
                # Логируем активность
                VotingParticipation.objects.get_or_create(user=request.user, voting=voting)
        
        messages.success(request, "Ваш голос принят!")
        return redirect('voting_detail', voting_id=voting.id) # PRG паттерн: редирект после POST

    user_votes = {}
    if request.user.is_authenticated:
        votes = Vote.objects.filter(user=request.user, participant__nomination__voting=voting)
        for v in votes:
            user_votes[v.participant.nomination.id] = v.participant.id

    return render(request, 'voting/detail.html', {
        'voting': voting,
        'user_votes': user_votes,
        'is_finished': not voting.is_active(),
    })


def voting_stats(request):
    raw_data = Voting.objects.values('title', 'start_date')
    titles_only = Voting.objects.values_list('title', flat=True)
    
    return render(request, 'voting/stats.html', {
        'raw_data': raw_data,
        'titles_only': titles_only
    })


@login_required
def voting_create(request):
    if request.method == "POST":
        form = VotingForm(request.POST, request.FILES)
        if form.is_valid():
            voting = form.save(commit=False)
            voting.owner = request.user
            voting.save()
            return redirect('index')
    else:
        form = VotingForm()
    
    return render(request, 'voting/voting_form.html', {
        'form': form, 
        'title': 'Создать голосование',
        'btn_text': 'Создать голосование' 
    })


@login_required
def voting_update(request, pk):
    voting = get_object_or_404(Voting, pk=pk)
    if voting.owner != request.user and not request.user.is_staff:
        return redirect('index')

    if request.method == "POST":
        form = VotingForm(request.POST, request.FILES, instance=voting)
        if form.is_valid():
            form.save()
            return redirect('voting_detail', voting_id=voting.id)
    else:
        form = VotingForm(instance=voting)
        
    return render(request, 'voting/voting_form.html', {
        'form': form, 
        'title': 'Редактировать', 
        'btn_text': 'Сохранить изменения'
    })


@login_required
def voting_delete(request, pk):
    voting = get_object_or_404(Voting, pk=pk)
    if voting.owner != request.user and not request.user.is_staff:
        return redirect('index')

    if request.method == "POST":
        voting.delete()
        return redirect('index')
    return render(request, 'voting/voting_confirm_delete.html', {'voting': voting})


@login_required
def vote(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    nomination = participant.nomination

    already_voted = Vote.objects.filter(
        user=request.user, 
        participant__nomination=nomination
    ).exists()

    if not already_voted:
        Vote.objects.create(user=request.user, participant=participant)
        VotingParticipation.objects.get_or_create(
            user=request.user, 
            voting=nomination.voting
        )

    return redirect('voting_detail', voting_id=nomination.voting.id)


@login_required
def unvote(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    Vote.objects.filter(
        user=request.user, 
        participant__nomination=participant.nomination
    ).delete()
    return redirect('voting_detail', voting_id=participant.nomination.voting.id)


@login_required
def archive_old_votings(request):
    if request.user.is_staff:
        Voting.objects.filter(end_date__lt=now()).update(voting_type='private')
        
    return redirect('index')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'voting/register.html', {'form': form})


@login_required
def profile_votings(request):
    user_votings = Voting.objects.filter(owner=request.user).order_by('-created_at')
    current_time = now()
    
    draft_votings = user_votings.filter(voting_type='private')
    
    active_votings = user_votings.filter(
        Q(voting_type='public') | Q(voting_type='invite_only'),
        start_date__lte=current_time,
        end_date__gte=current_time
    )
    
    archive_votings = user_votings.filter(
        Q(voting_type='public') | Q(voting_type='invite_only'),
        end_date__lt=current_time
    )
    
    return render(request, 'voting/profile.html', {
        'draft_votings': draft_votings,
        'active_votings': active_votings,
        'archive_votings': archive_votings,
    })

