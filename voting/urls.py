from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, viewsets
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register(r'votings', viewsets.VotingViewSet)
router.register(r'nominations', viewsets.NominationViewSet)
router.register(r'participants', viewsets.ParticipantViewSet)
router.register(r'votes', viewsets.VoteViewSet)
router.register(r'widgets/news', viewsets.WidgetNewsViewSet)
router.register(r'widgets/polls', viewsets.WidgetDailyPollViewSet)
router.register(r'widgets/top', viewsets.WidgetTopVotingViewSet)

urlpatterns = [
    path('', views.main_page, name='main'),
    path('all/', views.index, name='index'),
    path('profile/', views.profile_votings, name='profile_votings'),
    path('voting/create/', views.voting_create, name='voting_create'),
    path('voting/<int:pk>/edit/', views.voting_update, name='voting_update'),
    path('voting/<int:pk>/delete/', views.voting_delete, name='voting_delete'),
    path('voting/<int:voting_id>/', views.voting_detail, name='voting_detail'),
    path('vote/<int:participant_id>/', views.vote, name='vote'),
    path('unvote/<int:participant_id>/', views.unvote, name='unvote'),
    path('register/', views.register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')), 
    path('api/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)