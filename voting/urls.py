from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, viewsets

# Настройка API роутера
router = DefaultRouter()
router.register(r'votings', viewsets.VotingViewSet)
router.register(r'nominations', viewsets.NominationViewSet)
router.register(r'participants', viewsets.ParticipantViewSet)
router.register(r'votes', viewsets.VoteViewSet)

urlpatterns = [
    # Веб-интерфейс (HTML)
    path('', views.index, name='index'),
    
    # Задание 4: Маршруты для CRUD
    path('voting/create/', views.voting_create, name='voting_create'),
    path('voting/<int:pk>/edit/', views.voting_update, name='voting_update'),
    path('voting/<int:pk>/delete/', views.voting_delete, name='voting_delete'),
    
    path('voting/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('vote/<int:participant_id>/', views.vote, name='vote'),
    path('unvote/<int:participant_id>/', views.unvote, name='unvote'),
    path('register/', views.register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')), 

    # API
    path('api/', include(router.urls)),
]