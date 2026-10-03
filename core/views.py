from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from datetime import timedelta, datetime
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from django.db.models import F
from django.views.decorators.http import require_POST
import json

from .models import (
    Sport, Coach, Tournament, Team, Player,
    Match, MatchEvent, CoachOverrideLog, AILineupLog, TeamInvitation
)
from .ai_engine import AIRecEngine


# ----------------------------------------------------
# AUTHENTICATION & RBAC
# ----------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_msg = None
    success_msg = request.GET.get('registered')
    if success_msg:
        success_msg = "Registration successful! You can now log in with your credentials."

    if request.method == 'POST':
        action = request.POST.get('action', 'login')

        if action == 'register':
            u = request.POST.get('username', '').strip()
            p = request.POST.get('password', '').strip()
            name = request.POST.get('full_name', '').strip()
            email = request.POST.get('email', '').strip()
            role = request.POST.get('role', 'Forward')
            sport_id = request.POST.get('sport')
            team_id = request.POST.get('team')

            try:
                jersey = int(request.POST.get('jersey_number', 10))
                age = int(request.POST.get('age', 21))
            except (TypeError, ValueError):
                jersey, age = 10, 21

            if not u or not p or not name:
                error_msg = "Please fill in all mandatory registration fields."
            elif User.objects.filter(username=u).exists():
                error_msg = f"Username '{u}' is already taken. Please choose another."
            else:
                sport = Sport.objects.filter(id=sport_id).first() or Sport.objects.first()
                team = Team.objects.filter(id=team_id).first() if team_id else None
                if sport is None:
                    error_msg = "No sport is configured yet. Please seed or create a sport first."
                elif team and team.sport_id != sport.id:
                    error_msg = "Selected team does not belong to the selected sport."
                else:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=u, email=email, password=p, first_name=name
                        )
                        existing_profile = Player.objects.filter(email__iexact=email).first() if email else None
                        if existing_profile and existing_profile.user_id is None:
                            existing_profile.user = user
                            existing_profile.name = name or existing_profile.name
                            existing_profile.jersey_number = jersey
                            existing_profile.sport = sport
                            if team:
                                existing_profile.team = team
                            existing_profile.role = role
                            existing_profile.age = age
                            existing_profile.save(update_fields=['user','name','jersey_number','sport','team','role','age'])
                        else:
                            Player.objects.create(
                                user=user, email=email,
                                name=name, jersey_number=jersey, sport=sport, team=team,
                                role=role, age=age, fitness_score=95, injury_status='FIT',
                                recent_form=8.0, stamina_rating=85, pace_rating=85, tactical_awareness=80,
                                preferred_ground=request.POST.get('preferred_ground', 'Any'),
                                preferred_weather=request.POST.get('preferred_weather', 'Any'),
                            )
                    login(request, user)
                    return redirect('dashboard')
        else:
            u = request.POST.get('username', '').strip()
            p = request.POST.get('password', '')
            selected_role = request.POST.get('role', 'admin').lower()
            user = authenticate(request, username=u, password=p)

            if user is not None:
                is_admin = user.is_staff or user.is_superuser
                is_coach = hasattr(user, 'coach_profile')
                is_player = hasattr(user, 'player_profile')

                role_ok = (
                    (selected_role == 'admin' and is_admin)
                    or (selected_role == 'coach' and is_coach)
                    or (selected_role == 'player' and is_player)
                )
                if role_ok:
                    login(request, user)
                    return redirect('dashboard')
                error_msg = f"This account is not registered as a {selected_role.title()}."
            else:
                error_msg = "Invalid username or password. Please try again."

    teams = Team.objects.all()
    sports = Sport.objects.all()

    return render(request, 'login.html', {
        'error': error_msg,
        'success': success_msg,
        'teams': teams,
        'sports': sports,
    })


def logout_view(request):
    logout(request)
    return redirect('login')


# ----------------------------------------------------
# DASHBOARD
# ----------------------------------------------------

@login_required
def dashboard_view(request):
    user = request.user
    is_coach = hasattr(user, 'coach_profile')
    is_player = hasattr(user, 'player_profile')
    coach = user.coach_profile if is_coach else None
    player = user.player_profile if is_player else None

    # Player self-service team controls
    player_invitations = TeamInvitation.objects.filter(email__iexact=user.email, status='PENDING').select_related('team', 'invited_by') if is_player and user.email else TeamInvitation.objects.none()
    available_join_teams = Team.objects.select_related('sport').filter(sport_id=player.sport_id).exclude(id=player.team_id) if is_player and player and not player.team_id else Team.objects.none()
    managed_team_players = player.team.players.select_related('user').order_by('created_at','id') if is_player and player and player.team_id else Player.objects.none()

    # Base Querysets
    if is_coach and coach:
        managed_teams = coach.managed_teams.all().prefetch_related('players')
        if not managed_teams.exists():
            managed_teams = Team.objects.filter(
                Q(home_matches__status__in=['SCHEDULED','LIVE']) |
                Q(away_matches__status__in=['SCHEDULED','LIVE'])
            ).distinct().prefetch_related('players')
        players_count = Player.objects.filter(team__in=managed_teams).count()
        teams_count = managed_teams.count()
        upcoming_matches = Match.objects.filter(
            Q(home_team__in=managed_teams) | Q(away_team__in=managed_teams),
            status__in=['SCHEDULED', 'LIVE']
        ).order_by('scheduled_time')[:12]
        recent_matches = Match.objects.filter(
            Q(home_team__in=managed_teams) | Q(away_team__in=managed_teams),
            status='COMPLETED'
        ).order_by('-scheduled_time')[:12]
        override_logs = CoachOverrideLog.objects.filter(coach=coach).order_by('-timestamp')[:8]
    else:
        managed_teams = Team.objects.all()
        players_count = Player.objects.count()
        teams_count = Team.objects.count()
        upcoming_matches = Match.objects.filter(status__in=['SCHEDULED', 'LIVE']).order_by('scheduled_time')[:12]
        recent_matches = Match.objects.filter(status='COMPLETED').order_by('-scheduled_time')[:12]
        override_logs = CoachOverrideLog.objects.all().order_by('-timestamp')[:8]

    # Always rebuild standings from completed match history so analytics never depend on stale counters.
    _refresh_team_standings()
    chart_teams = list(Team.objects.select_related('sport').order_by('-wins', '-draws', 'name')[:12])
    team_chart_data = [
        {'label': t.short_code, 'wins': t.wins, 'draws': t.draws, 'losses': t.losses, 'win_rate': t.win_rate}
        for t in chart_teams
    ]

    # Metrics are scoped to the logged-in role where appropriate.
    if is_coach:
        metric_players = Player.objects.filter(team__in=managed_teams)
    elif is_player and player and player.team_id:
        metric_players = Player.objects.filter(team=player.team)
    else:
        metric_players = Player.objects.all()

    fit_players_count = metric_players.filter(injury_status='FIT').count()
    injured_players_count = metric_players.filter(injury_status='INJURED').count()
    minor_issue_count = metric_players.filter(injury_status='MINOR_ISSUE').count()
    # IMPORTANT: upcoming_matches is sliced above for the dashboard cards.
    # Django does not allow filtering a QuerySet after a slice has been taken.
    # Count live fixtures from a fresh unsliced queryset instead.
    live_matches_count = Match.objects.filter(status='LIVE').count()
    tournaments_count = Tournament.objects.count()

    # Calculate squad avg fitness & form
    avg_fitness = metric_players.aggregate(avg=Avg('fitness_score'))['avg'] or 0
    avg_form = metric_players.aggregate(avg=Avg('recent_form'))['avg'] or 0

    context = {
        'is_coach': is_coach,
        'is_player': is_player,
        'player': player,
        'coach': coach,
        'sports': Sport.objects.all(),
        'player_invitations': player_invitations,
        'available_join_teams': available_join_teams,
        'managed_team_players': managed_team_players,
        'team_chart_data': team_chart_data,
        'players_count': players_count,
        'teams_count': teams_count,
        'fit_players_count': fit_players_count,
        'injured_players_count': injured_players_count,
        'minor_issue_count': minor_issue_count,
        'live_matches_count': live_matches_count,
        'tournaments_count': tournaments_count,
        'avg_fitness': round(avg_fitness, 1),
        'avg_form': round(avg_form, 1),
        'upcoming_matches': upcoming_matches,
        'recent_matches': recent_matches,
        'override_logs': override_logs,
        'teams': managed_teams,
    }
    return render(request, 'dashboard.html', context)


# ----------------------------------------------------
# PLAYERS MODULE (FR-2.1 to FR-2.5)
# ----------------------------------------------------

@login_required
def players_view(request):
    role_filter = request.GET.get('role', '')
    team_filter = request.GET.get('team', '')
    injury_filter = request.GET.get('injury', '')
    search_query = request.GET.get('q', '')

    players = Player.objects.select_related('team', 'sport').all().order_by('jersey_number')

    if role_filter:
        players = players.filter(role=role_filter)
    if team_filter:
        players = players.filter(team_id=team_filter)
    if injury_filter:
        players = players.filter(injury_status=injury_filter)
    if search_query:
        players = players.filter(Q(name__icontains=search_query) | Q(role__icontains=search_query))

    teams = Team.objects.all()
    sports = Sport.objects.all()
    coaches = Coach.objects.all()

    context = {
        'players': players,
        'teams': teams,
        'sports': sports,
        'coaches': coaches,
        'selected_role': role_filter,
        'selected_team': team_filter,
        'selected_injury': injury_filter,
        'search_query': search_query,
    }
    return render(request, 'players.html', context)


@login_required
@require_POST
def player_add_view(request):
    try:
        name = (request.POST.get('name') or '').strip()
        sport_id = request.POST.get('sport')
        team_id = request.POST.get('team') or None
        role = (request.POST.get('role') or 'Forward').strip()
        if not name: raise ValueError('Athlete name is required.')
        sport = Sport.objects.filter(id=sport_id).first()
        if not sport: raise ValueError('Please select a valid sport.')
        team = Team.objects.filter(id=team_id).first() if team_id else None
        if team and team.sport_id != sport.id: raise ValueError('Selected team does not belong to the selected sport.')
        jersey_number = int(request.POST.get('jersey_number', 10)); age = int(request.POST.get('age', 22))
        fitness_score = int(request.POST.get('fitness_score', 90)); recent_form = float(request.POST.get('recent_form', 7.5))
        if not 0 <= fitness_score <= 100 or not 1 <= recent_form <= 10: raise ValueError('Fitness must be 0-100 and recent form must be 1-10.')
        Player.objects.create(name=name,email=(request.POST.get('email') or '').strip().lower(),sport=sport,team=team,role=role,jersey_number=jersey_number,age=age,fitness_score=fitness_score,
            injury_status=request.POST.get('injury_status','FIT'),recent_form=recent_form,preferred_ground=request.POST.get('preferred_ground','Any'),
            preferred_weather=request.POST.get('preferred_weather','Any'),stamina_rating=float(request.POST.get('stamina_rating',85)),
            pace_rating=float(request.POST.get('pace_rating',82)),tactical_awareness=float(request.POST.get('tactical_awareness',80)))
        messages.success(request,f'Athlete {name} was added successfully.')
    except Exception as e: messages.error(request,f'Could not add athlete: {e}')
    return redirect('players')

@login_required
@require_POST
def player_edit_view(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    try:
        player.name = request.POST.get('name', player.name)
        player.email = (request.POST.get('email', player.email) or '').strip().lower()
        player.role = request.POST.get('role', player.role)
        player.jersey_number = int(request.POST.get('jersey_number', player.jersey_number))
        player.age = int(request.POST.get('age', player.age))
        player.fitness_score = int(request.POST.get('fitness_score', player.fitness_score))
        player.injury_status = request.POST.get('injury_status', player.injury_status)
        player.recent_form = float(request.POST.get('recent_form', player.recent_form))
        player.preferred_ground = request.POST.get('preferred_ground', player.preferred_ground)
        player.preferred_weather = request.POST.get('preferred_weather', player.preferred_weather)
        player.is_available_for_matchday = request.POST.get('is_available') == 'on'
        
        team_id = request.POST.get('team')
        player.team = Team.objects.filter(id=team_id).first() if team_id else None
        player.save()
        return redirect('players')
    except Exception as e:
        return HttpResponse(f"Error updating player: {str(e)}", status=400)


@login_required
@require_POST
def player_delete_view(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    player.delete()
    return redirect('players')


@login_required
def api_player_detail(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    data = {
        'id': player.id,
        'name': player.name,
        'jersey_number': player.jersey_number,
        'team_name': player.team.name if player.team else 'Free Agent',
        'team_id': player.team.id if player.team else None,
        'sport': player.sport.name,
        'role': player.role,
        'age': player.age,
        'fitness_score': player.fitness_score,
        'injury_status': player.injury_status,
        'recent_form': player.recent_form,
        'matches_played': player.matches_played,
        'goals_scored': player.goals_scored,
        'assists': player.assists,
        'tackles': player.tackles_or_defenses,
        'stamina': player.stamina_rating,
        'pace': player.pace_rating,
        'tactics': player.tactical_awareness,
        'preferred_ground': player.preferred_ground,
        'preferred_weather': player.preferred_weather,
        'is_available': player.is_available_for_matchday,
    }
    return JsonResponse(data)


# ----------------------------------------------------
# PLAYER TEAM SELF-SERVICE
# ----------------------------------------------------

@login_required
@require_POST
def player_create_team_view(request):
    player = getattr(request.user, 'player_profile', None)
    if player is None:
        messages.error(request, 'Only a player account can create a team from Player Hub.')
        return redirect('dashboard')
    if player.team_id:
        messages.error(request, f'You are already a member of {player.team.name}. Leave that team before creating another one.')
        return redirect('dashboard')

    try:
        name = (request.POST.get('name') or '').strip()
        short_code = (request.POST.get('short_code') or '').strip().upper()
        sport = Sport.objects.filter(id=request.POST.get('sport')).first()
        home_ground = (request.POST.get('home_ground') or 'Indus Central Stadium').strip()
        if not name or not sport:
            raise ValueError('Team name and sport are required.')
        if Team.objects.filter(name__iexact=name).exists():
            raise ValueError('A team with this name already exists.')
        if not short_code:
            short_code = ''.join(c for c in name if c.isalnum())[:6].upper() or 'TEAM'
        if Team.objects.filter(short_code__iexact=short_code).exists():
            raise ValueError('That team code is already in use.')

        member_names = request.POST.getlist('member_name[]')
        member_emails = request.POST.getlist('member_email[]')
        cleaned = []
        seen = set()
        for member_name, email in zip(member_names, member_emails):
            member_name = member_name.strip()
            email = email.strip().lower()
            if not member_name and not email:
                continue
            if not member_name or not email or '@' not in email:
                raise ValueError('Every invited teammate needs both a name and a valid Gmail/email address.')
            if email == request.user.email.lower():
                continue
            if email in seen:
                raise ValueError(f'Duplicate teammate email: {email}')
            seen.add(email)
            cleaned.append((member_name, email))

        required_extra = max(int(sport.lineup_size) - 1, 0)
        max_extra = max(int(sport.lineup_size + sport.bench_size) - 1, required_extra)
        if len(cleaned) < required_extra:
            raise ValueError(f'{sport.name} requires {sport.lineup_size} active players. Add at least {required_extra} teammate profile(s); you are already one player.')
        if len(cleaned) > max_extra:
            raise ValueError(f'{sport.name} allows up to {max_extra} additional teammate profiles including the bench.')

        with transaction.atomic():
            team = Team.objects.create(name=name, short_code=short_code, sport=sport, home_ground=home_ground, owner=player)
            player.team = team
            player.sport = sport
            if not player.email and request.user.email:
                player.email = request.user.email.lower()
            player.save(update_fields=['team', 'sport', 'email'])
            for member_name, email in cleaned:
                existing_user = User.objects.filter(email__iexact=email).first()
                existing_player = getattr(existing_user, 'player_profile', None) if existing_user else Player.objects.filter(email__iexact=email).first()
                if existing_player and existing_player.team_id and existing_player.team_id != team.id:
                    raise ValueError(f'{email} is already assigned to another team.')
                if existing_player is None:
                    existing_player = Player.objects.create(
                        name=member_name, email=email, sport=sport, team=team,
                        role='Forward' if sport.name == 'Football' else 'Player',
                        jersey_number=10 + len(cleaned), age=21,
                        fitness_score=90, injury_status='FIT', recent_form=8.0
                    )
                    invite_status = 'PENDING'
                else:
                    existing_player.team = team
                    existing_player.sport = sport
                    existing_player.name = member_name
                    existing_player.email = email
                    existing_player.save(update_fields=['team','sport','name','email'])
                    invite_status = 'ACCEPTED' if existing_player.user_id else 'PENDING'
                invite = TeamInvitation.objects.create(
                    team=team, invited_by=player, player=existing_player,
                    member_name=member_name, email=email, status=invite_status
                )
                if invite_status == 'ACCEPTED':
                    invite.accepted_at = timezone.now()
                    invite.save(update_fields=['accepted_at'])

        messages.success(request, f'{team.name} created. Your teammate invitations are saved; matching registered accounts were added automatically.')
    except Exception as e:
        messages.error(request, f'Could not create team: {e}')
    return redirect('dashboard')


@login_required
@require_POST
def player_team_add_member_view(request):
    player = getattr(request.user, 'player_profile', None)
    if not player or not player.team_id or player.team.owner_id != player.id:
        messages.error(request, 'Only the team owner can manage this team roster.')
        return redirect('dashboard')
    team = player.team
    try:
        name = (request.POST.get('member_name') or '').strip()
        email = (request.POST.get('member_email') or '').strip().lower()
        role = (request.POST.get('member_role') or 'Forward').strip()
        jersey = int(request.POST.get('member_jersey') or 10)
        if not name or '@' not in email:
            raise ValueError('Member name and a valid email are required.')
        max_roster = team.sport.lineup_size + team.sport.bench_size
        if team.players.count() >= max_roster:
            raise ValueError(f'{team.sport.name} squad is already at the maximum {max_roster} player profiles.')
        if Player.objects.filter(team=team, email__iexact=email).exists():
            raise ValueError('That player is already in your team.')
        existing_user = User.objects.filter(email__iexact=email).first()
        existing = getattr(existing_user, 'player_profile', None) if existing_user else Player.objects.filter(email__iexact=email).first()
        if existing and existing.team_id and existing.team_id != team.id:
            raise ValueError('That player is already a member of another team.')
        with transaction.atomic():
            if existing:
                existing.team = team
                existing.sport = team.sport
                existing.name = name
                existing.email = email
                existing.role = role
                existing.jersey_number = jersey
                existing.save(update_fields=['team','sport','name','email','role','jersey_number'])
                target = existing
            else:
                target = Player.objects.create(name=name,email=email,team=team,sport=team.sport,role=role,jersey_number=jersey,age=21,fitness_score=95,recent_form=8.0)
            invite, _ = TeamInvitation.objects.get_or_create(team=team,email=email,defaults={'invited_by':player,'player':target,'member_name':name})
            invite.player = target; invite.member_name = name; invite.status = 'ACCEPTED'; invite.accepted_at = timezone.now(); invite.save()
        messages.success(request, f'{name} was added to {team.name}.')
    except Exception as e:
        messages.error(request, f'Could not add team member: {e}')
    return redirect('dashboard')

@login_required
@require_POST
def player_team_remove_member_view(request, player_id):
    owner = getattr(request.user, 'player_profile', None)
    if not owner or not owner.team_id or owner.team.owner_id != owner.id:
        messages.error(request, 'Only the team owner can manage this roster.')
        return redirect('dashboard')
    member = get_object_or_404(Player, id=player_id, team_id=owner.team_id)
    if member.id == owner.id:
        messages.error(request, 'The team owner cannot be removed. Transfer ownership first by leaving the team.')
        return redirect('dashboard')
    member.team = None
    member.save(update_fields=['team'])
    TeamInvitation.objects.filter(team_id=owner.team_id, player=member).update(status='DECLINED')
    messages.success(request, f'{member.name} was removed from {owner.team.name}.')
    return redirect('dashboard')

@login_required
@require_POST
def player_team_edit_member_view(request, player_id):
    owner = getattr(request.user, 'player_profile', None)
    if not owner or not owner.team_id or owner.team.owner_id != owner.id:
        messages.error(request, 'Only the team owner can edit this roster.')
        return redirect('dashboard')
    member = get_object_or_404(Player, id=player_id, team_id=owner.team_id)
    try:
        name = (request.POST.get('member_name') or member.name).strip()
        email = (request.POST.get('member_email') or member.email).strip().lower()
        role = (request.POST.get('member_role') or member.role).strip()
        jersey = int(request.POST.get('member_jersey') or member.jersey_number)
        if not name or '@' not in email:
            raise ValueError('Name and a valid email are required.')
        duplicate = Player.objects.filter(team=owner.team, email__iexact=email).exclude(id=member.id).exists()
        if duplicate:
            raise ValueError('Another player in this team already uses that email.')
        member.name = name
        member.email = email
        member.role = role
        member.jersey_number = jersey
        member.save(update_fields=['name','email','role','jersey_number'])
        TeamInvitation.objects.filter(team=owner.team, player=member).update(member_name=name, email=email)
        messages.success(request, f'{member.name} was updated successfully.')
    except Exception as e:
        messages.error(request, f'Could not update player: {e}')
    return redirect('dashboard')


@login_required
@require_POST
def player_join_team_view(request):
    player = getattr(request.user, 'player_profile', None)
    if player is None:
        messages.error(request, 'Only a player account can join a team from Player Hub.')
        return redirect('dashboard')
    team = Team.objects.filter(id=request.POST.get('team_id')).first()
    join_code = (request.POST.get('join_code') or '').strip().upper()
    if not team and join_code:
        team = Team.objects.filter(short_code__iexact=join_code).first()
    if not team:
        messages.error(request, 'Select a team or enter a valid team code.')
        return redirect('dashboard')
    if team.sport_id != player.sport_id:
        messages.error(request, 'You can only join a team for your registered sport.')
        return redirect('dashboard')
    if team.players.count() >= team.sport.lineup_size + team.sport.bench_size:
        messages.error(request, f'{team.name} has reached its maximum {team.sport.lineup_size + team.sport.bench_size}-player roster.')
        return redirect('dashboard')
    if player.team_id == team.id:
        messages.info(request, f'You are already a member of {team.name}.')
        return redirect('dashboard')
    if player.team_id:
        messages.error(request, f'You are already in {player.team.name}. Leave that team before joining another team.')
        return redirect('dashboard')

    invitation = TeamInvitation.objects.filter(team=team, email__iexact=request.user.email, status='PENDING').first()
    player.team = team
    if not player.email and request.user.email:
        player.email = request.user.email.lower()
    player.save(update_fields=['team', 'email'])
    if invitation:
        invitation.player = player
        invitation.status = 'ACCEPTED'
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=['player', 'status', 'accepted_at'])
    messages.success(request, f'You joined {team.name} successfully.')
    return redirect('dashboard')


@login_required
@require_POST
def player_leave_team_view(request):
    player = getattr(request.user, 'player_profile', None)
    if player is None or player.team_id is None:
        messages.info(request, 'You are not currently in a team.')
        return redirect('dashboard')
    old_team = player.team
    next_owner = old_team.players.exclude(id=player.id).order_by('created_at','id').first()
    if old_team.owner_id == player.id:
        old_team.owner = next_owner
        old_team.save(update_fields=['owner'])
    player.team = None
    player.save(update_fields=['team'])
    messages.success(request, f'You left {old_team.name}. You can now create or join another team.')
    return redirect('dashboard')


# ----------------------------------------------------
# TEAMS MODULE (FR-3.1 to FR-3.5)
# ----------------------------------------------------

@login_required
def teams_view(request):
    teams = Team.objects.select_related('sport', 'coach').prefetch_related('players').all()
    coaches = Coach.objects.all()
    sports = Sport.objects.all()
    context = {
        'teams': teams,
        'coaches': coaches,
        'sports': sports,
    }
    return render(request, 'teams.html', context)


@login_required
@require_POST
def team_add_view(request):
    try:
        name=(request.POST.get('name') or '').strip(); short_code=(request.POST.get('short_code') or '').strip().upper()
        sport_id=request.POST.get('sport'); coach_id=request.POST.get('coach') or None
        if not name: raise ValueError('Team name is required.')
        if not short_code: short_code=''.join(ch for ch in name if ch.isalnum())[:6].upper() or 'TEAM'
        sport=Sport.objects.filter(id=sport_id).first()
        if not sport: raise ValueError('Please select a valid sport.')
        if Team.objects.filter(name__iexact=name).exists(): raise ValueError('A team with this name already exists.')
        if Team.objects.filter(short_code__iexact=short_code).exists(): raise ValueError(f'Short code {short_code} is already in use.')
        coach=Coach.objects.filter(id=coach_id).first() if coach_id else None
        Team.objects.create(name=name,short_code=short_code,sport=sport,coach=coach,primary_color=request.POST.get('primary_color','#10B981'),home_ground=(request.POST.get('home_ground') or 'Arena').strip())
        messages.success(request,f'Team {name} was created successfully.')
    except Exception as e: messages.error(request,f'Could not create team: {e}')
    return redirect('teams')

@login_required
def team_detail_view(request, team_id):
    team = get_object_or_404(Team.objects.select_related('coach', 'sport'), id=team_id)
    players = team.players.all()
    free_agents = Player.objects.filter(team__isnull=True, sport=team.sport)
    matches = Match.objects.filter(Q(home_team=team) | Q(away_team=team)).order_by('-scheduled_time')

    context = {
        'team': team,
        'players': players,
        'free_agents': free_agents,
        'matches': matches,
    }
    return render(request, 'team_detail.html', context)


# ----------------------------------------------------
# MATCHES MODULE (FR-4.1 to FR-4.5)
# ----------------------------------------------------

@login_required
def matches_view(request):
    _refresh_team_standings()
    status_filter = request.GET.get('status', '')
    matches = Match.objects.select_related('home_team', 'away_team', 'tournament', 'sport').all().order_by('-scheduled_time')
    
    if status_filter:
        matches = matches.filter(status=status_filter)

    teams = Team.objects.all()
    tournaments = Tournament.objects.all()
    sports = Sport.objects.all()

    context = {
        'matches': matches,
        'teams': teams,
        'tournaments': tournaments,
        'sports': sports,
        'selected_status': status_filter,
    }
    return render(request, 'matches.html', context)


@login_required
@require_POST
def match_schedule_view(request):
    try:
        home_team=Team.objects.filter(id=request.POST.get('home_team')).first(); away_team=Team.objects.filter(id=request.POST.get('away_team')).first()
        tournament=Tournament.objects.filter(id=request.POST.get('tournament')).first() if request.POST.get('tournament') else None
        dt=parse_datetime(request.POST.get('scheduled_time') or ''); venue=(request.POST.get('venue') or '').strip()
        ground_type=request.POST.get('ground_type','Grass'); weather=request.POST.get('weather','Sunny')
        if not home_team or not away_team: raise ValueError('Please select both home and away teams.')
        if home_team.id==away_team.id: raise ValueError('Home and away teams must be different.')
        if home_team.sport_id!=away_team.sport_id: raise ValueError('Home and away teams must play the same sport.')
        if tournament and tournament.sport_id!=home_team.sport_id: raise ValueError("Tournament sport must match the teams' sport.")
        if not dt: raise ValueError('Please provide a valid match date and time.')
        if timezone.is_naive(dt): dt=timezone.make_aware(dt,timezone.get_current_timezone())
        if not venue: raise ValueError('A venue is required.')
        if Match.objects.filter(home_team=home_team,away_team=away_team,scheduled_time=dt,status__in=['SCHEDULED','LIVE']).exists(): raise ValueError('This fixture already exists at the selected date and time.')
        Match.objects.create(home_team=home_team,away_team=away_team,sport=home_team.sport,tournament=tournament,scheduled_time=dt,venue=venue,ground_type=ground_type,weather=weather,status='SCHEDULED')
        messages.success(request,f'Fixture {home_team.short_code} vs {away_team.short_code} scheduled successfully.')
    except Exception as e: messages.error(request,f'Could not schedule fixture: {e}')
    return redirect('matches')

@login_required
def ai_recommendations_view(request):
    matches = Match.objects.select_related('home_team', 'away_team').filter(status__in=['SCHEDULED', 'LIVE'])
    teams = Team.objects.all()
    context = {
        'matches': matches,
        'teams': teams,
    }
    return render(request, 'ai_recommendations.html', context)


@login_required
def api_run_ai_lineup(request):
    team_id = request.GET.get('team_id')
    match_id = request.GET.get('match_id')
    ground_type = request.GET.get('ground_type', 'Grass')
    weather = request.GET.get('weather', 'Sunny')

    team = get_object_or_404(Team, id=team_id)
    match_obj = Match.objects.filter(id=match_id).first() if match_id else None

    if match_obj:
        ground_type = ground_type or match_obj.ground_type
        weather = weather or match_obj.weather

    players = list(team.players.all())
    ai_result = AIRecEngine.recommend_lineup(
        players=players,
        sport_name=team.sport.name,
        match_ground=ground_type,
        match_weather=weather
    )

    # Save to AILineupLog if match exists
    if match_obj:
        AILineupLog.objects.create(
            match=match_obj,
            team=team,
            confidence_percentage=ai_result['overall_confidence'],
            weather_condition=weather,
            ground_type=ground_type,
            lineup_json=json.dumps(ai_result['starting_xi']),
            factors_summary_json=json.dumps(ai_result['factors'])
        )

    return JsonResponse({
        'status': 'success',
        'team_name': team.name,
        'ground_type': ground_type,
        'weather': weather,
        'confidence': ai_result['overall_confidence'],
        'factors': ai_result['factors'],
        'starting_xi': ai_result['starting_xi'],
        'bench': ai_result['bench'],
        'all_ranked': ai_result['all_ranked']
    })


# ----------------------------------------------------
# COACH PORTAL & MATCHDAY CONTROLS (FR-6.1 to FR-6.8)
# ----------------------------------------------------

@login_required
def coach_portal_view(request):
    user = request.user
    is_player = hasattr(user, 'player_profile')
    is_coach = hasattr(user, 'coach_profile')

    if is_player and not (user.is_staff or user.is_superuser):
        messages.error(request, 'Coach Matchday is available only to coaches and administrators.')
        return redirect('dashboard')

    if is_coach:
        coach = user.coach_profile
        teams = coach.managed_teams.all().prefetch_related('players').order_by('name')
        # If a legacy database has a coach without an assigned team, still provide
        # useful matchday controls rather than an empty screen.
        if not teams.exists():
            teams = Team.objects.filter(
                Q(home_matches__status__in=['SCHEDULED','LIVE']) |
                Q(away_matches__status__in=['SCHEDULED','LIVE'])
            ).distinct().prefetch_related('players').order_by('name')
        upcoming_matches = Match.objects.filter(
            Q(home_team__in=teams) | Q(away_team__in=teams),
            status__in=['SCHEDULED', 'LIVE']
        ).select_related('home_team', 'away_team', 'sport', 'tournament').order_by('scheduled_time')[:40]
        logs = CoachOverrideLog.objects.filter(coach=coach).order_by('-timestamp')[:20]
    else:
        coach = Coach.objects.first()
        teams = Team.objects.all().prefetch_related('players').order_by('name')
        upcoming_matches = Match.objects.filter(
            status__in=['SCHEDULED', 'LIVE']
        ).select_related('home_team', 'away_team', 'sport', 'tournament').order_by('scheduled_time')[:40]
        logs = CoachOverrideLog.objects.all().order_by('-timestamp')[:20]

    context = {
        'coach': coach,
        'teams': teams,
        'upcoming_matches': upcoming_matches,
        'logs': logs,
        'fixture_count': len(upcoming_matches),
        'team_count': teams.count(),
    }
    return render(request, 'coach_portal.html', context)


@login_required
@require_POST
def api_coach_substitute(request):
    try:
        data=json.loads(request.body or '{}'); match_obj=get_object_or_404(Match.objects.select_related('home_team','away_team'),id=data.get('match_id'))
        out_player=get_object_or_404(Player,id=data.get('outgoing_player_id')); in_player=get_object_or_404(Player,id=data.get('incoming_player_id')); reason=(data.get('reason') or '').strip()
        if match_obj.status not in ['SCHEDULED','LIVE']: raise ValueError('Substitutions are only allowed for scheduled or live fixtures.')
        if len(reason)<5: raise ValueError('A valid reason (minimum 5 characters) is mandatory.')
        if out_player.id==in_player.id: raise ValueError('Outgoing and replacement athletes must be different.')
        if out_player.team_id!=in_player.team_id: raise ValueError('Replacement player must belong to the same team roster.')
        if out_player.team_id not in [match_obj.home_team_id,match_obj.away_team_id]: raise ValueError('The selected athlete is not on a team participating in this match.')
        if not out_player.is_available_for_matchday: raise ValueError('The outgoing athlete is already unavailable for matchday.')
        if in_player.injury_status=='INJURED' or not in_player.is_available_for_matchday: raise ValueError('Replacement athlete must be available and not injured.')
        lineup = AIRecEngine.recommend_lineup(list(out_player.team.players.all()), out_player.team.sport.name, match_obj.ground_type, match_obj.weather)
        starting_ids = {p['player_id'] for p in lineup['starting_xi']}
        bench_ids = {p['player_id'] for p in lineup['bench']}
        if out_player.id not in starting_ids:
            raise ValueError('Outgoing athlete is not currently in the AI starting lineup for this match.')
        if in_player.id not in bench_ids:
            raise ValueError('Replacement athlete must come from the eligible bench.')
        coach=getattr(request.user,'coach_profile',None)
        if coach is None: coach=match_obj.home_team.coach if out_player.team_id==match_obj.home_team_id else match_obj.away_team.coach
        if coach is None: raise ValueError('No coach profile is available to record this override.')
        if hasattr(request.user,'coach_profile'):
            managed_ids = list(request.user.coach_profile.managed_teams.values_list('id', flat=True))
            if managed_ids and out_player.team_id not in managed_ids:
                raise ValueError('You can only substitute players from teams you manage.')
        with transaction.atomic():
            if 'injur' in reason.lower(): out_player.injury_status='INJURED'
            out_player.is_available_for_matchday=False
            out_player.save(update_fields=['injury_status','is_available_for_matchday'])
            in_player.is_available_for_matchday=True
            in_player.save(update_fields=['is_available_for_matchday'])
            log_entry=CoachOverrideLog.objects.create(match=match_obj,coach=coach,action_type='SUBSTITUTION',outgoing_player=out_player,incoming_player=in_player,reason=reason,ai_recalculated=True)
            team_players=list(out_player.team.players.all()); updated_ai=AIRecEngine.recommend_lineup(players=team_players,sport_name=out_player.team.sport.name,match_ground=match_obj.ground_type,match_weather=match_obj.weather)
            AILineupLog.objects.create(match=match_obj,team=out_player.team,confidence_percentage=updated_ai['overall_confidence'],weather_condition=match_obj.weather,ground_type=match_obj.ground_type,lineup_json=json.dumps(updated_ai['starting_xi']),factors_summary_json=json.dumps(updated_ai['factors']))
        return JsonResponse({'status':'success','message':f'Emergency substitution confirmed: #{in_player.jersey_number} {in_player.name} in for #{out_player.jersey_number} {out_player.name}.','log_id':log_entry.id,'timestamp':log_entry.timestamp.strftime('%Y-%m-%d %H:%M:%S'),'updated_ai_confidence':updated_ai['overall_confidence'],'new_starting_xi':updated_ai['starting_xi']})
    except Exception as e: return JsonResponse({'status':'error','message':str(e)},status=400)

@login_required
@require_POST
def api_coach_venue_change(request):
    try:
        data=json.loads(request.body or '{}'); match_obj=get_object_or_404(Match.objects.select_related('home_team','away_team'),id=data.get('match_id'))
        new_venue=(data.get('new_venue') or '').strip(); new_ground_type=data.get('new_ground_type','Turf'); reason=(data.get('reason') or '').strip()
        if match_obj.status not in ['SCHEDULED','LIVE']: raise ValueError('Venue overrides are only allowed for scheduled or live fixtures.')
        if not new_venue or len(reason)<5: raise ValueError('Alternate venue and a justification of at least 5 characters are required.')
        coach=getattr(request.user,'coach_profile',None) or match_obj.home_team.coach or match_obj.away_team.coach
        if coach is None: raise ValueError('No coach profile is available to record this override.')
        if hasattr(request.user,'coach_profile'):
            managed_ids=list(request.user.coach_profile.managed_teams.values_list('id',flat=True))
            if managed_ids and match_obj.home_team_id not in managed_ids and match_obj.away_team_id not in managed_ids:
                raise ValueError('You can only change venues for fixtures involving your managed teams.')
        old_venue=match_obj.venue
        with transaction.atomic():
            match_obj.venue=new_venue; match_obj.ground_type=new_ground_type; match_obj.save(update_fields=['venue','ground_type'])
            log_entry=CoachOverrideLog.objects.create(match=match_obj,coach=coach,action_type='VENUE_CHANGE',old_venue=old_venue,new_venue=new_venue,reason=reason,ai_recalculated=True)
            home_players=list(match_obj.home_team.players.all()); updated_ai=AIRecEngine.recommend_lineup(players=home_players,sport_name=match_obj.home_team.sport.name,match_ground=new_ground_type,match_weather=match_obj.weather)
            AILineupLog.objects.create(match=match_obj,team=match_obj.home_team,confidence_percentage=updated_ai['overall_confidence'],weather_condition=match_obj.weather,ground_type=new_ground_type,lineup_json=json.dumps(updated_ai['starting_xi']),factors_summary_json=json.dumps(updated_ai['factors']))
        return JsonResponse({'status':'success','message':f"Match venue changed from '{old_venue}' to '{new_venue}' ({new_ground_type}). AI lineup re-evaluated.",'new_venue':new_venue,'new_ground_type':new_ground_type,'updated_ai_confidence':updated_ai['overall_confidence'],'log_id':log_entry.id})
    except Exception as e: return JsonResponse({'status':'error','message':str(e)},status=400)

def _apply_match_result(match_obj):
    """Synchronize team W/L/D totals without double-counting results."""
    if match_obj.home_team_id == match_obj.away_team_id:
        raise ValueError("A match must have two different teams.")

    home = match_obj.home_team
    away = match_obj.away_team

    previous_status = getattr(match_obj, '_previous_status', None)
    previous_winner_id = getattr(match_obj, '_previous_winner_id', None)
    previous_draw = getattr(match_obj, '_previous_is_draw', False)
    previous_recorded = getattr(match_obj, '_previous_standings_recorded', False)

    # Remove a result only when this application's previous save actually
    # recorded it in team totals.
    if previous_status == 'COMPLETED' and previous_recorded:
        if previous_draw:
            home.draws = max(0, home.draws - 1)
            away.draws = max(0, away.draws - 1)
        elif previous_winner_id == home.id:
            home.wins = max(0, home.wins - 1)
            away.losses = max(0, away.losses - 1)
        elif previous_winner_id == away.id:
            away.wins = max(0, away.wins - 1)
            home.losses = max(0, home.losses - 1)

    if match_obj.status == 'COMPLETED':
        if match_obj.home_score > match_obj.away_score:
            match_obj.winner = home
            match_obj.is_draw = False
        elif match_obj.away_score > match_obj.home_score:
            match_obj.winner = away
            match_obj.is_draw = False
        else:
            match_obj.winner = None
            match_obj.is_draw = True

        # New completion, or editing a result that was already recorded.
        should_record = (
            previous_status != 'COMPLETED'
            or previous_recorded
        )
        if should_record:
            if match_obj.is_draw:
                home.draws += 1
                away.draws += 1
            elif match_obj.winner_id == home.id:
                home.wins += 1
                away.losses += 1
            else:
                away.wins += 1
                home.losses += 1
            match_obj.standings_recorded = True
    else:
        match_obj.winner = None
        match_obj.is_draw = False
        # If a previously recorded completed result is reopened, its old
        # contribution was removed above and must not remain marked recorded.
        if previous_status == 'COMPLETED' and previous_recorded:
            match_obj.standings_recorded = False

    home.save(update_fields=['wins', 'losses', 'draws'])
    away.save(update_fields=['wins', 'losses', 'draws'])
    match_obj.save(update_fields=[
        'home_score', 'away_score', 'status', 'winner', 'is_draw',
        'standings_recorded', 'summary_notes'
    ])


# ----------------------------------------------------
# LIVE MATCHDAY SCORER & TIMELINE (FR-4.2, FR-4.4, FR-4.5)
# ----------------------------------------------------

@login_required
def live_match_view(request, match_id):
    match_obj = get_object_or_404(
        Match.objects.select_related('home_team', 'away_team', 'sport', 'tournament'),
        id=match_id
    )
    events = match_obj.events.all()
    home_players = match_obj.home_team.players.all()
    away_players = match_obj.away_team.players.all()

    context = {
        'match': match_obj,
        'events': events,
        'home_players': home_players,
        'away_players': away_players,
    }
    return render(request, 'live_match.html', context)


@login_required
@require_POST
def api_update_match_score(request, match_id):
    match_obj = get_object_or_404(Match.objects.select_related('home_team', 'away_team'), id=match_id)
    try:
        data = json.loads(request.body or '{}')
        home_score = int(data.get('home_score', match_obj.home_score))
        away_score = int(data.get('away_score', match_obj.away_score))
        status = data.get('status', match_obj.status)

        if home_score < 0 or away_score < 0:
            raise ValueError("Scores cannot be negative.")
        if status not in dict(Match.STATUS_CHOICES):
            raise ValueError("Invalid match status.")

        with transaction.atomic():
            match_obj._previous_status = match_obj.status
            match_obj._previous_winner_id = match_obj.winner_id
            match_obj._previous_is_draw = match_obj.is_draw
            match_obj._previous_standings_recorded = match_obj.standings_recorded

            match_obj.home_score = home_score
            match_obj.away_score = away_score
            match_obj.status = status
            _apply_match_result(match_obj)

        return JsonResponse({
            'status': 'success',
            'home_score': match_obj.home_score,
            'away_score': match_obj.away_score,
            'match_status': match_obj.status,
            'winner': match_obj.winner.name if match_obj.winner else ('Draw' if match_obj.is_draw else None)
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
@require_POST
def api_add_match_event(request, match_id):
    match_obj = get_object_or_404(
        Match.objects.select_related('home_team', 'away_team'), id=match_id
    )
    try:
        if match_obj.status == 'COMPLETED':
            raise ValueError("Cannot add events to a completed match.")

        data = json.loads(request.body or '{}')
        minute = int(data.get('minute', 1))
        event_type = data.get('event_type', 'GOAL')
        team_id = data.get('team_id')
        player_id = data.get('player_id')
        description = (data.get('description') or '').strip()

        valid_event_types = dict(MatchEvent.EVENT_TYPES)
        if event_type not in valid_event_types:
            raise ValueError("Invalid event type.")
        if minute < 1 or minute > 120:
            raise ValueError("Match minute must be between 1 and 120.")
        if not description:
            raise ValueError("Event description is required.")

        team = Team.objects.filter(
            id=team_id
        ).filter(Q(id=match_obj.home_team_id) | Q(id=match_obj.away_team_id)).first()
        if team is None:
            raise ValueError("Selected team is not participating in this match.")

        player = Player.objects.filter(id=player_id, team=team).first() if player_id else None

        with transaction.atomic():
            event = MatchEvent.objects.create(
                match=match_obj,
                minute=minute,
                event_type=event_type,
                team=team,
                player=player,
                description=description
            )

            if player:
                if event_type == 'GOAL':
                    player.goals_scored += 1
                elif event_type == 'ASSIST':
                    player.assists += 1
                player.save(update_fields=['goals_scored', 'assists'])

            # Goal/point events are score-bearing events, so keep the scoreboard
            # synchronized with the timeline.
            if event_type in ('GOAL', 'POINT'):
                if team.id == match_obj.home_team_id:
                    match_obj.home_score += 1
                else:
                    match_obj.away_score += 1
                match_obj.save(update_fields=['home_score', 'away_score'])

        return JsonResponse({
            'status': 'success',
            'event_id': event.id,
            'minute': event.minute,
            'event_type': event.event_type,
            'team': team.short_code,
            'player': player.name if player else '',
            'description': event.description,
            'home_score': match_obj.home_score,
            'away_score': match_obj.away_score,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def _refresh_team_standings():
    teams = list(Team.objects.all())
    if not teams:
        return
    for team in teams:
        completed = Match.objects.filter(status='COMPLETED').filter(Q(home_team_id=team.id) | Q(away_team_id=team.id))
        wins = completed.filter(winner_id=team.id).count()
        draws = completed.filter(is_draw=True).count()
        losses = completed.filter(is_draw=False).exclude(winner_id=team.id).exclude(winner__isnull=True).count()
        if (team.wins, team.draws, team.losses) != (wins, draws, losses):
            Team.objects.filter(pk=team.id).update(wins=wins, draws=draws, losses=losses)


# ----------------------------------------------------
# REPORTS & ANALYTICS MODULE (FR-7.1 to FR-7.5)
# ----------------------------------------------------

@login_required
def reports_view(request):
    _refresh_team_standings()
    players = Player.objects.all().order_by('-recent_form')[:15]
    teams = Team.objects.all().order_by('-wins')
    tournaments = Tournament.objects.all()
    recent_matches = Match.objects.filter(status='COMPLETED').order_by('-scheduled_time')[:10]

    # Aggregates for visual charts
    role_distribution = list(Player.objects.values('role').annotate(count=Count('id')).order_by('-count'))
    report_team_data = [{'label': t.short_code, 'wins': t.wins, 'draws': t.draws, 'losses': t.losses, 'win_rate': t.win_rate} for t in teams[:15]]
    fitness_distribution = {
        'Fit': Player.objects.filter(injury_status='FIT').count(),
        'Minor Issue': Player.objects.filter(injury_status='MINOR_ISSUE').count(),
        'Injured': Player.objects.filter(injury_status='INJURED').count(),
    }

    context = {
        'top_players': players,
        'players_count_total': Player.objects.count(),
        'teams': teams,
        'tournaments': tournaments,
        'recent_matches': recent_matches,
        'completed_matches_count': Match.objects.filter(status='COMPLETED').count(),
        'role_distribution': role_distribution,
        'fitness_distribution': json.dumps(fitness_distribution),
        'report_team_data': report_team_data,
    }
    return render(request, 'reports.html', context)


# ----------------------------------------------------
# MATCH HISTORY & DATE-WISE RESULTS / WINNERS (NEW FEATURE)
# ----------------------------------------------------

@login_required
def match_history_view(request):
    _refresh_team_standings()
    date_filter = request.GET.get('date', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    preset = request.GET.get('preset', 'all').strip()
    team_filter = request.GET.get('team', '').strip()
    sport_filter = request.GET.get('sport', '').strip()
    tournament_filter = request.GET.get('tournament', '').strip()
    search_query = request.GET.get('q', '').strip()

    matches = Match.objects.select_related('home_team', 'away_team', 'winner', 'sport', 'tournament')\
                           .prefetch_related('events').filter(status='COMPLETED').order_by('-scheduled_time')

    now = timezone.now()
    today_date = now.date()

    if preset == 'today':
        matches = matches.filter(scheduled_time__date=today_date)
    elif preset == 'yesterday':
        matches = matches.filter(scheduled_time__date=today_date - timedelta(days=1))
    elif preset == 'last7':
        matches = matches.filter(scheduled_time__date__gte=today_date - timedelta(days=7))
    elif preset == 'last30':
        matches = matches.filter(scheduled_time__date__gte=today_date - timedelta(days=30))
    elif date_filter:
        matches = matches.filter(scheduled_time__date=date_filter)
    elif start_date and end_date:
        matches = matches.filter(scheduled_time__date__gte=start_date, scheduled_time__date__lte=end_date)
    elif start_date:
        matches = matches.filter(scheduled_time__date__gte=start_date)
    elif end_date:
        matches = matches.filter(scheduled_time__date__lte=end_date)

    if team_filter:
        matches = matches.filter(Q(home_team_id=team_filter) | Q(away_team_id=team_filter))
    if sport_filter:
        matches = matches.filter(sport_id=sport_filter)
    if tournament_filter:
        matches = matches.filter(tournament_id=tournament_filter)
    if search_query:
        matches = matches.filter(
            Q(home_team__name__icontains=search_query) |
            Q(away_team__name__icontains=search_query) |
            Q(venue__icontains=search_query) |
            Q(summary_notes__icontains=search_query)
        )

    # Group matches by Date (Date-wise winners & summary)
    date_grouped = {}
    total_goals = 0
    total_matches = 0
    winner_counts = {}

    for m in matches:
        m_date = m.scheduled_time.date()
        if m_date not in date_grouped:
            date_grouped[m_date] = {
                'date': m_date,
                'formatted_date': m_date.strftime("%A, %B %d, %Y"),
                'is_today': (m_date == today_date),
                'matches': [],
                'daily_winners': [],
                'daily_goals': 0,
                'total_matches': 0,
            }
        
        date_grouped[m_date]['matches'].append(m)
        date_grouped[m_date]['total_matches'] += 1
        m_goals = m.home_score + m.away_score
        date_grouped[m_date]['daily_goals'] += m_goals
        total_goals += m_goals
        total_matches += 1

        if m.winner:
            date_grouped[m_date]['daily_winners'].append({
                'team': m.winner,
                'scoreline': f"{m.home_score} - {m.away_score}",
                'match': m,
                'opponent': m.away_team if m.winner == m.home_team else m.home_team
            })
            winner_counts[m.winner.name] = winner_counts.get(m.winner.name, 0) + 1

    # Convert dictionary to sorted list of date cards
    grouped_history = sorted(date_grouped.values(), key=lambda x: x['date'], reverse=True)

    # Top winning team overall
    top_winner_name = max(winner_counts, key=winner_counts.get) if winner_counts else "N/A"
    top_winner_count = winner_counts.get(top_winner_name, 0)

    teams = Team.objects.all()
    sports = Sport.objects.all()
    tournaments = Tournament.objects.all()

    context = {
        'grouped_history': grouped_history,
        'total_matches': total_matches,
        'total_goals': total_goals,
        'avg_goals': round(total_goals / total_matches, 1) if total_matches > 0 else 0,
        'top_winner_name': top_winner_name,
        'top_winner_count': top_winner_count,
        'teams': teams,
        'sports': sports,
        'tournaments': tournaments,
        'selected_date': date_filter,
        'selected_preset': preset,
        'selected_team': team_filter,
        'selected_sport': sport_filter,
        'selected_tournament': tournament_filter,
        'start_date': start_date,
        'end_date': end_date,
        'search_query': search_query,
    }
    return render(request, 'match_history.html', context)


def _pdf_styles():
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    styles = getSampleStyleSheet()
    return colors, styles, ParagraphStyle('SportHubTitle', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#0F172A'), alignment=TA_CENTER, spaceAfter=10), ParagraphStyle('SportHubSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#475569'), alignment=TA_CENTER, spaceAfter=16)

@login_required
def reports_export_pdf_view(request):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib import colors
    _refresh_team_standings()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="SportsHub_Executive_Report_2026.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
    colors_, styles, title_style, sub_style = _pdf_styles()
    story = [Paragraph('SportsHub 2026 Performance Analytics', title_style), Paragraph(f'Executive report • Generated {timezone.localtime():%d %B %Y, %I:%M %p} IST', sub_style)]
    teams = list(Team.objects.select_related('sport').order_by('-wins','-draws','name')[:15])
    players = list(Player.objects.select_related('team','sport').order_by('-recent_form','-fitness_score')[:20])
    completed = Match.objects.filter(status='COMPLETED').count()
    story.append(Table([['Active Teams', str(Team.objects.count()), 'Tracked Athletes', str(Player.objects.count()), 'Completed Fixtures', str(completed), 'Tournaments', str(Tournament.objects.count())]], colWidths=[85,55,95,65,110,65,80,55], style=TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0F766E')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#CBD5E1')),('FONTSIZE',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)])))
    story += [Spacer(1,14), Paragraph('Team Standings', styles['Heading2'])]
    rows=[['Team','Sport','Wins','Draws','Losses','Win Rate']]+[[t.short_code,t.sport.name,str(t.wins),str(t.draws),str(t.losses),f'{t.win_rate}%'] for t in teams]
    story.append(Table(rows, repeatRows=1, colWidths=[120,100,60,60,60,75], style=TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1E293B')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#CBD5E1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')]),('ALIGN',(2,1),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])))
    story += [Spacer(1,14), Paragraph('Top Performing Athletes', styles['Heading2'])]
    rows=[['Athlete','Club','Role','Fitness','Form','Goals','Assists']]+[[p.name,p.team.short_code if p.team else 'Free Agent',p.role,f'{p.fitness_score}%',f'{p.recent_form}/10',str(p.goals_scored),str(p.assists)] for p in players]
    story.append(Table(rows, repeatRows=1, colWidths=[150,100,100,65,65,55,55], style=TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0F766E')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#CBD5E1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')]),('ALIGN',(3,1),(-1,-1),'CENTER'),('FONTSIZE',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)])))
    doc.build(story)
    return response

@login_required
def match_history_export_pdf_view(request):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
    from reportlab.lib import colors
    _refresh_team_standings()
    matches = list(Match.objects.filter(status='COMPLETED').select_related('home_team','away_team','winner','sport').prefetch_related('events').order_by('-scheduled_time')[:120])
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="SportsHub_Match_History.pdf"'
    doc = SimpleDocTemplate(response, pagesize=landscape(A4), rightMargin=20,leftMargin=20,topMargin=20,bottomMargin=20)
    colors_, styles, title_style, sub_style = _pdf_styles()
    story=[Paragraph('SportsHub Match History & Winners',title_style),Paragraph(f'{len(matches)} latest completed fixtures • Generated {timezone.localtime():%d %B %Y, %I:%M %p} IST',sub_style)]
    rows=[['Date','Fixture','Score','Winner','Venue','Sport']]
    for m in matches:
        rows.append([m.scheduled_time.strftime('%d-%m-%Y'),f'{m.home_team.short_code} vs {m.away_team.short_code}',f'{m.home_score} - {m.away_score}',m.winner.name if m.winner else 'Draw',m.venue,m.sport.name])
    story.append(Table(rows,repeatRows=1,colWidths=[70,120,55,130,230,70],style=TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1E293B')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#CBD5E1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F8FAFC')]),('FONTSIZE',(0,0),(-1,-1),7.5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)])))
    doc.build(story)
    return response

# ----------------------------------------------------
# AUDIT LOGS (FR-6.7, 5.7)
# ----------------------------------------------------

@login_required
def audit_logs_view(request):
    logs = CoachOverrideLog.objects.select_related('match', 'coach', 'outgoing_player', 'incoming_player').all().order_by('-timestamp')
    ai_logs = AILineupLog.objects.select_related('match', 'team').all().order_by('-created_at')[:20]

    context = {
        'logs': logs,
        'ai_logs': ai_logs,
    }
    return render(request, 'audit_logs.html', context)

