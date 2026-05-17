from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.utils.timezone import now
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q, F


from .models import Voting, Nomination, Participant, Vote, VotingParticipation
from .forms import VotingForm

# ------------------ 1. ОТОБРАЖЕНИЕ И ПОИСК (Задание 6) ------------------

def index(request):
    """Главная страница с поиском через __icontains и пагинацией"""
    # 1. Получаем поисковый запрос из URL (параметр ?q=)
    query = request.GET.get('q', '').strip()
    
    # 2. Базовый QuerySet (Безопасность: фильтрация по правам доступа)
    if request.user.is_authenticated:
        votings_qs = Voting.objects.filter(
            Q(voting_type='public') | Q(owner=request.user)
        )
    else:
        votings_qs = Voting.objects.filter(voting_type='public')

    # 3. ЗАДАНИЕ 6: Применяем поиск (фильтрация по подстроке без учета регистра)
    if query:
        votings_qs = votings_qs.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    # 4. ОПТИМИЗАЦИЯ: select_related (JOIN) и prefetch_related (доп. запрос для списков)
    # Это решает проблему N+1 запросов к базе данных.
    votings_list = votings_qs.select_related('owner').prefetch_related('nominations').order_by("-created_at")
    
    # 5. Пагинация (Задание про списки объектов)
    paginator = Paginator(votings_list, 8) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'voting/index.html', {
        'page_obj': page_obj,
        'query': query,
        'current_time': now()
    })

def voting_detail(request, voting_id):
    """Детальная страница (Задание 5: get_object_or_404)"""
    # get_object_or_404 автоматически вернет 404 ошибку, если ID не существует
    voting = get_object_or_404(
        Voting.objects.select_related('owner').prefetch_related('nominations__participants'), 
        pk=voting_id
    )
    
    #добавляем "виртуальное" поле с количеством участников к каждой номинации
    nominations = voting.nominations.annotate(
        participants_count_attr=Count('participants')
    )

    # ЗАДАНИЕ 6: Использование метода count() для агрегации данных
    total_votes_in_voting = Vote.objects.filter(participant__nomination__voting=voting).count()

    # Словарь для хранения голосов текущего пользователя (подсветка выбора в шаблоне)
    user_votes = {}
    if request.user.is_authenticated:
        votes = Vote.objects.filter(
            user=request.user,
            participant__nomination__voting=voting
        )
        for v in votes:
            user_votes[v.participant.nomination.id] = v.participant.id

    return render(request, 'voting/detail.html', {
        'voting': voting,
        'nominations': nominations,
        'user_votes': user_votes,
        'total_votes': total_votes_in_voting,
        'is_finished': voting.is_finished(),
    })

# ------------------ 2. ОПТИМИЗАЦИЯ ВЫБОРКИ (Задание 6) ------------------

def voting_stats(request):
    """Демонстрация values() и values_list()"""
    # values() — возвращает список словарей (только нужные поля, экономит память)
    raw_data = Voting.objects.values('title', 'start_date')
    titles_only = Voting.objects.values_list('title', flat=True)
    
    return render(request, 'voting/stats.html', {
        'raw_data': raw_data,
        'titles_only': titles_only
    })

# ------------------ 3. CRUD: ОПЕРАЦИИ (Задание 5: Создание, Редактирование, Удаление) ------------------

@login_required # Декоратор: запрещает доступ неавторизованным (Задание про безопасность)
def voting_create(request):
    if request.method == "POST":
        # request.FILES нужен для загрузки файлов/изображений
        form = VotingForm(request.POST, request.FILES)
        if form.is_valid():
            # commit=False позволяет дописать автора перед сохранением в БД
            voting = form.save(commit=False)
            voting.owner = request.user
            voting.save()
            return redirect('index') # redirect — редирект после успешного действия
    else:
        form = VotingForm()
    
    return render(request, 'voting/voting_form.html', {
        'form': form, 
        'title': 'Создать',
        'btn_text': 'Создать голосование' 
    })

@login_required
def voting_update(request, pk):
    voting = get_object_or_404(Voting, pk=pk)
    # Проверка прав: только владелец или персонал может редактировать
    if voting.owner != request.user and not request.user.is_staff:
        return redirect('index')

    if request.method == "POST":
        form = VotingForm(request.POST, request.FILES, instance=voting)
        if form.is_valid():
            form.save()
            return redirect('voting_detail', voting_id=voting.id)
    else:
        form = VotingForm(instance=voting)
    return render(request, 'voting/voting_form.html', {'form': form, 'title': 'Редактировать'})

@login_required
def voting_delete(request, pk):
    voting = get_object_or_404(Voting, pk=pk)
    if voting.owner != request.user and not request.user.is_staff:
        return redirect('index')

    if request.method == "POST":
        voting.delete()
        return redirect('index')
    return render(request, 'voting/voting_confirm_delete.html', {'voting': voting})

# ------------------ 4. ЛОГИКА ГОЛОСОВАНИЯ (Задание 6) ------------------

@login_required
def vote(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    nomination = participant.nomination

    # ЗАДАНИЕ 6: exists() — самый быстрый способ проверить наличие записи в БД
    already_voted = Vote.objects.filter(
        user=request.user, 
        participant__nomination=nomination
    ).exists()

    if not already_voted:
        # Создаем запись о голосе
        Vote.objects.create(user=request.user, participant=participant)
        # Связываем пользователя с голосованием (промежуточная таблица)
        VotingParticipation.objects.get_or_create(
            user=request.user, 
            voting=nomination.voting
        )

    return redirect('voting_detail', voting_id=nomination.voting.id)

@login_required
def unvote(request, participant_id):
    participant = get_object_or_404(Participant, pk=participant_id)
    # ЗАДАНИЕ 6: Массовое удаление через delete() на QuerySet
    Vote.objects.filter(
        user=request.user, 
        participant__nomination=participant.nomination
    ).delete()
    return redirect('voting_detail', voting_id=participant.nomination.voting.id)

# ------------------ 5. МАССОВЫЕ ОПЕРАЦИИ (Задание 6) ------------------

@login_required
def archive_old_votings(request):
    """Пример использования update() для массового изменения записей"""
    if request.user.is_staff:
        Voting.objects.filter(end_date__lt=now()).update(voting_type='private')
        
    return redirect('index')

# ------------------ 6. АККАУНТЫ (Регистрация) ------------------

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Автоматический вход после регистрации
            return redirect('index')
    else:
        form = UserCreationForm()
    return render(request, 'voting/register.html', {'form': form})