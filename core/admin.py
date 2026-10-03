from django.contrib import admin
from .models import (
    Sport, Coach, Tournament, Team, Player,
    Match, MatchEvent, CoachOverrideLog, AILineupLog, TeamInvitation
)

@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'lineup_size', 'bench_size')

@admin.register(Coach)
class CoachAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'license_level', 'specialization', 'phone')

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'sport', 'status', 'start_date', 'location')

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_code', 'sport', 'coach', 'wins', 'losses', 'draws')
    search_fields = ('name', 'short_code')

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'jersey_number', 'team', 'role', 'fitness_score', 'injury_status', 'recent_form')
    list_filter = ('sport', 'team', 'injury_status', 'role')
    search_fields = ('name',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'home_team', 'away_team', 'scheduled_time', 'venue', 'status', 'home_score', 'away_score')
    list_filter = ('status', 'sport', 'tournament')

@admin.register(MatchEvent)
class MatchEventAdmin(admin.ModelAdmin):
    list_display = ('match', 'minute', 'event_type', 'team', 'player')

@admin.register(CoachOverrideLog)
class CoachOverrideLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'coach', 'match', 'action_type', 'timestamp', 'ai_recalculated')
    readonly_fields = ('timestamp',)

@admin.register(AILineupLog)
class AILineupLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'team', 'match', 'confidence_percentage', 'created_at')


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ('team', 'member_name', 'email', 'status', 'invited_by', 'created_at', 'accepted_at')
    list_filter = ('status', 'team__sport')
    search_fields = ('team__name', 'member_name', 'email')
    readonly_fields = ('created_at', 'accepted_at')
