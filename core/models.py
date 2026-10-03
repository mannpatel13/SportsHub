from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json

class Sport(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, unique=True)
    icon = models.CharField(max_length=50, default='activity')
    lineup_size = models.PositiveIntegerField(default=11)
    bench_size = models.PositiveIntegerField(default=7)

    def __str__(self):
        return self.name


class Coach(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile')
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=25, blank=True, null=True)
    license_level = models.CharField(max_length=50, default='UEFA A / Level 3')
    specialization = models.CharField(max_length=100, default='Tactical & High Performance')
    bio = models.TextField(blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.user.username})"


class Tournament(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('ACTIVE', 'Active / In-Progress'),
        ('COMPLETED', 'Completed'),
    ]
    name = models.CharField(max_length=150)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='tournaments')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=120, default='Indus University Arena')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.sport.name})"


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    short_code = models.CharField(max_length=10, unique=True)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='teams')
    coach = models.ForeignKey(Coach, on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_teams')
    owner = models.ForeignKey('Player', on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_teams')
    primary_color = models.CharField(max_length=20, default='#10B981') # vibrant neon/emerald
    secondary_color = models.CharField(max_length=20, default='#0F172A')
    home_ground = models.CharField(max_length=120, default='Indus Central Stadium')
    logo_symbol = models.CharField(max_length=30, default='shield')
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_matches(self):
        return self.wins + self.losses + self.draws

    @property
    def win_rate(self):
        if self.total_matches == 0:
            return 0
        return round((self.wins / self.total_matches) * 100, 1)

    def __str__(self):
        return f"{self.name} [{self.short_code}]"


class Player(models.Model):
    INJURY_STATUS = [
        ('FIT', 'Match Fit (100%)'),
        ('MINOR_ISSUE', 'Minor Issue / Fatigue (70%)'),
        ('INJURED', 'Injured / Sidelined (0%)'),
    ]
    GROUND_PREFERENCES = [
        ('Any', 'All Grounds'),
        ('Grass', 'Natural Grass'),
        ('Turf', 'Artificial Turf'),
        ('Clay', 'Clay / Hard Court'),
        ('Indoor', 'Indoor Arena'),
    ]
    WEATHER_PREFERENCES = [
        ('Any', 'All Weather'),
        ('Sunny', 'Sunny & Dry'),
        ('Rainy', 'Wet & Rainy'),
        ('Humid', 'Humid Conditions'),
        ('Windy', 'High Wind Resistance'),
        ('Overcast', 'Overcast / Cool'),
    ]

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='player_profile')
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, default='')
    jersey_number = models.PositiveIntegerField(default=10)
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='players')
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    role = models.CharField(max_length=50, default='Forward') # e.g. Forward, Midfielder, Defender, Goalkeeper
    age = models.PositiveIntegerField(default=22)
    fitness_score = models.PositiveIntegerField(default=95) # 0 to 100
    injury_status = models.CharField(max_length=20, choices=INJURY_STATUS, default='FIT')
    recent_form = models.FloatField(default=8.5) # 1.0 to 10.0
    
    # Granular performance metrics
    matches_played = models.PositiveIntegerField(default=12)
    goals_scored = models.PositiveIntegerField(default=6)
    assists = models.PositiveIntegerField(default=4)
    tackles_or_defenses = models.PositiveIntegerField(default=18)
    stamina_rating = models.FloatField(default=88.0) # 0-100
    pace_rating = models.FloatField(default=85.0) # 0-100
    tactical_awareness = models.FloatField(default=82.0) # 0-100
    
    preferred_ground = models.CharField(max_length=20, choices=GROUND_PREFERENCES, default='Any')
    preferred_weather = models.CharField(max_length=20, choices=WEATHER_PREFERENCES, default='Any')
    
    is_available_for_matchday = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def injury_badge_class(self):
        if self.injury_status == 'FIT':
            return 'badge-success'
        elif self.injury_status == 'MINOR_ISSUE':
            return 'badge-warning'
        return 'badge-danger'

    def __str__(self):
        return f"#{self.jersey_number} {self.name} ({self.role} - {self.team.name if self.team else 'Free Agent'})"


class TeamInvitation(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
    ]
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_team_invitations')
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='team_invitations')
    member_name = models.CharField(max_length=120)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['team', 'email'], name='unique_team_invite_email'),
        ]

    def __str__(self):
        return f"{self.team.name} -> {self.member_name} <{self.email}> ({self.status})"


class Match(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live in Progress'),
        ('COMPLETED', 'Completed / Final'),
        ('CANCELLED', 'Postponed / Cancelled'),
    ]
    GROUND_TYPES = [
        ('Grass', 'Natural Grass'),
        ('Turf', 'Artificial Turf'),
        ('Clay', 'Clay Pitch'),
        ('Indoor', 'Indoor Arena'),
    ]
    WEATHER_CONDITIONS = [
        ('Sunny', 'Clear & Sunny (28°C)'),
        ('Rainy', 'Heavy Rain & Wet (19°C)'),
        ('Humid', 'High Humidity & Heat (32°C)'),
        ('Windy', 'High Wind Gusts (22°C)'),
        ('Overcast', 'Overcast & Mild (24°C)'),
    ]

    tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches')
    sport = models.ForeignKey(Sport, on_delete=models.CASCADE, related_name='matches')
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='away_matches')
    scheduled_time = models.DateTimeField(default=timezone.now)
    venue = models.CharField(max_length=150, default='Indus Main Stadium')
    ground_type = models.CharField(max_length=30, choices=GROUND_TYPES, default='Grass')
    weather = models.CharField(max_length=30, choices=WEATHER_CONDITIONS, default='Sunny')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    
    # Match Result & Score
    home_score = models.PositiveIntegerField(default=0)
    away_score = models.PositiveIntegerField(default=0)
    winner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    is_draw = models.BooleanField(default=False)
    standings_recorded = models.BooleanField(default=False, help_text='Whether this match result has been included in team W/L/D totals.')
    summary_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.home_team.short_code} vs {self.away_team.short_code} - {self.venue} ({self.status})"


class MatchEvent(models.Model):
    EVENT_TYPES = [
        ('GOAL', 'Goal / Score'),
        ('POINT', 'Point / Run'),
        ('ASSIST', 'Assist / Key Play'),
        ('YELLOW_CARD', 'Yellow Card Caution'),
        ('RED_CARD', 'Red Card Expulsion'),
        ('SUBSTITUTION', 'Player Substitution'),
        ('INJURY', 'Injury Stoppage'),
        ('FULL_TIME', 'Full Time Whistle'),
    ]
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events')
    minute = models.PositiveIntegerField(default=1)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['minute', 'created_at']

    def __str__(self):
        return f"{self.minute}' [{self.event_type}] {self.description}"


class CoachOverrideLog(models.Model):
    """
    SRS Requirement FR-6.6, FR-6.7, 5.7:
    Permanent, immutable audit trail for coach emergency substitutions, venue changes, and overrides.
    """
    ACTION_CHOICES = [
        ('SUBSTITUTION', 'Emergency Player Substitution'),
        ('VENUE_CHANGE', 'Weather / Ground Venue Override'),
        ('TACTICAL_OVERRIDE', 'Tactical Lineup Modification'),
    ]
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='override_logs')
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='override_logs')
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    
    # For player substitutions
    outgoing_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='subbed_out_logs')
    incoming_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, blank=True, related_name='subbed_in_logs')
    
    # For venue overrides
    old_venue = models.CharField(max_length=150, blank=True, null=True)
    new_venue = models.CharField(max_length=150, blank=True, null=True)
    
    reason = models.TextField(help_text="Detailed coach justification for override")
    timestamp = models.DateTimeField(default=timezone.now, editable=False)
    ai_recalculated = models.BooleanField(default=True, help_text="FR-6.8: True if AI engine auto re-evaluated")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.action_type}] Coach {self.coach.full_name} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class AILineupLog(models.Model):
    """
    SRS Requirement FR-5.4, 7.2:
    Stores history of AI recommendation runs, confidence scores, and factor snapshots for explainability and auditing.
    """
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='ai_lineup_logs')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='ai_lineup_logs')
    confidence_percentage = models.FloatField(default=92.5)
    weather_condition = models.CharField(max_length=50)
    ground_type = models.CharField(max_length=50)
    lineup_json = models.TextField(help_text="JSON serialized list of recommended starting XI and bench")
    factors_summary_json = models.TextField(help_text="JSON breakdown of weighted scoring parameters")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def lineup_data(self):
        try:
            return json.loads(self.lineup_json)
        except Exception:
            return []

    @property
    def factors_data(self):
        try:
            return json.loads(self.factors_summary_json)
        except Exception:
            return {}

    def __str__(self):
        return f"AI Lineup: {self.team.name} vs {self.match} ({self.confidence_percentage}%)"
