from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Players
    path('players/', views.players_view, name='players'),
    path('players/add/', views.player_add_view, name='player_add'),
    path('players/<int:player_id>/edit/', views.player_edit_view, name='player_edit'),
    path('players/<int:player_id>/delete/', views.player_delete_view, name='player_delete'),
    path('api/players/<int:player_id>/', views.api_player_detail, name='api_player_detail'),

    # Teams
    path('player/team/create/', views.player_create_team_view, name='player_create_team'),
    path('player/team/join/', views.player_join_team_view, name='player_join_team'),
    path('player/team/add-member/', views.player_team_add_member_view, name='player_team_add_member'),
    path('player/team/remove-member/<int:player_id>/', views.player_team_remove_member_view, name='player_team_remove_member'),
    path('player/team/edit-member/<int:player_id>/', views.player_team_edit_member_view, name='player_team_edit_member'),
    path('player/team/leave/', views.player_leave_team_view, name='player_leave_team'),
    path('teams/', views.teams_view, name='teams'),
    path('teams/add/', views.team_add_view, name='team_add'),
    path('teams/<int:team_id>/', views.team_detail_view, name='team_detail'),

    # Matches & History
    path('matches/', views.matches_view, name='matches'),
    path('matches/schedule/', views.match_schedule_view, name='match_schedule'),
    path('matches/<int:match_id>/live/', views.live_match_view, name='live_match'),
    path('match-history/', views.match_history_view, name='match_history'),
    path('api/matches/<int:match_id>/update-score/', views.api_update_match_score, name='api_update_match_score'),
    path('api/matches/<int:match_id>/add-event/', views.api_add_match_event, name='api_add_match_event'),

    # AI Recommendation Engine
    path('ai-recommendations/', views.ai_recommendations_view, name='ai_recommendations'),
    path('api/ai/run-lineup/', views.api_run_ai_lineup, name='api_run_ai_lineup'),

    # Coach Portal & Matchday Controls
    path('coach-portal/', views.coach_portal_view, name='coach_portal'),
    path('api/coach/substitute/', views.api_coach_substitute, name='api_coach_substitute'),
    path('api/coach/venue-change/', views.api_coach_venue_change, name='api_coach_venue_change'),

    # Reports & Analytics
    path('reports/', views.reports_view, name='reports'),
    path('reports/export/pdf/', views.reports_export_pdf_view, name='reports_export_pdf'),
    path('match-history/export/pdf/', views.match_history_export_pdf_view, name='match_history_export_pdf'),
]
