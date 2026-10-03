from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import random

from core.models import (
    Sport, Coach, Tournament, Team, Player,
    Match, MatchEvent, CoachOverrideLog, AILineupLog, TeamInvitation
)
from core.ai_engine import AIRecEngine
import json


class Command(BaseCommand):
    help = 'Seeds extensive realistic demo data for SportsHub with large dataset of teams, players, and date-wise matches'

    def handle(self, *args, **options):
        self.stdout.write("Flushing and re-seeding SportsHub database with very large realistic dataset...")

        # Clear existing matches, events, logs, players, teams for clean seed
        MatchEvent.objects.all().delete()
        CoachOverrideLog.objects.all().delete()
        AILineupLog.objects.all().delete()
        TeamInvitation.objects.all().delete()
        Match.objects.all().delete()
        Player.objects.all().delete()
        Team.objects.all().delete()
        Tournament.objects.all().delete()

        # 1. Admin User
        admin_user, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True, 'email': 'admin@sportshub.indus.edu'})
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password('admin123')
        admin_user.save()

        # 2. Coach Users
        coach_profiles_data = [
            {'username': 'coach_mann', 'pass': 'coach123', 'name': 'Mann Patel', 'lic': 'UEFA Pro License', 'spec': 'Tactical AI & High Intensity Transition', 'phone': '+91 98765 43210'},
            {'username': 'coach_riya', 'pass': 'coach123', 'name': 'Riya Patel', 'lic': 'UEFA A License', 'spec': 'Sports Science & Physical Conditioning', 'phone': '+91 98765 43211'},
            {'username': 'coach_marcus', 'pass': 'coach123', 'name': 'Marcus Vance', 'lic': 'AFC Elite Pro', 'spec': 'Defensive Solidity & Set Pieces', 'phone': '+91 98765 43212'},
            {'username': 'coach_arjun', 'pass': 'coach123', 'name': 'Arjun Kapoor', 'lic': 'AIFF Pro License', 'spec': 'Youth Development & Counter-Attacking', 'phone': '+91 98765 43213'},
            {'username': 'coach_smith', 'pass': 'coach123', 'name': 'Alex Smith', 'lic': 'UEFA Pro License', 'spec': 'Possession & Wing Play', 'phone': '+91 98765 43214'},
        ]

        coaches = []
        for c in coach_profiles_data:
            user, _ = User.objects.get_or_create(username=c['username'], defaults={'email': f"{c['username']}@sportshub.indus.edu"})
            user.set_password(c['pass'])
            user.save()

            coach, _ = Coach.objects.get_or_create(
                user=user,
                defaults={
                    'full_name': c['name'],
                    'phone': c['phone'],
                    'license_level': c['lic'],
                    'specialization': c['spec'],
                    'bio': f"Head strategist with expertise in {c['spec']}."
                }
            )
            coach.full_name = c['name']
            coach.license_level = c['lic']
            coach.specialization = c['spec']
            coach.save()
            coaches.append(coach)

        # 3. Player User account for player login
        player_user, _ = User.objects.get_or_create(username='player_aarav', defaults={'email': 'aarav@sportshub.indus.edu'})
        player_user.set_password('player123')
        player_user.save()

        # 4. Sports
        football, _ = Sport.objects.get_or_create(name='Football', defaults={'code': 'FB', 'icon': 'futbol', 'lineup_size': 11, 'bench_size': 7})
        cricket, _ = Sport.objects.get_or_create(name='Cricket', defaults={'code': 'CRIC', 'icon': 'baseball-bat-ball', 'lineup_size': 11, 'bench_size': 5})
        basketball, _ = Sport.objects.get_or_create(name='Basketball', defaults={'code': 'BB', 'icon': 'basketball', 'lineup_size': 5, 'bench_size': 5})
        volleyball, _ = Sport.objects.get_or_create(name='Volleyball', defaults={'code': 'VB', 'icon': 'volleyball', 'lineup_size': 6, 'bench_size': 6})
        tennis, _ = Sport.objects.get_or_create(name='Tennis', defaults={'code': 'TEN', 'icon': 'table-tennis-paddle-ball', 'lineup_size': 1, 'bench_size': 1})
        badminton, _ = Sport.objects.get_or_create(name='Badminton', defaults={'code': 'BAD', 'icon': 'feather-pointed', 'lineup_size': 1, 'bench_size': 2})

        # 5. Tournaments
        t1 = Tournament.objects.create(
            name='Indus Inter-University Premier Championship 2026',
            sport=football,
            start_date=timezone.now().date() - timedelta(days=25),
            end_date=timezone.now().date() + timedelta(days=20),
            location='Indus Central Stadium Arena, Ahmedabad',
            status='ACTIVE',
            description='The premier university football league featuring top western zone institutional clubs.'
        )

        t2 = Tournament.objects.create(
            name='All-India Collegiate Super Cup',
            sport=football,
            start_date=timezone.now().date() - timedelta(days=15),
            end_date=timezone.now().date() + timedelta(days=30),
            location='Salt Lake Sports Complex, Kolkata',
            status='ACTIVE',
            description='Knockout championship among elite collegiate franchises.'
        )

        t3 = Tournament.objects.create(
            name='Western Zone Inter-College League',
            sport=football,
            start_date=timezone.now().date() - timedelta(days=40),
            end_date=timezone.now().date() + timedelta(days=10),
            location='Shivaji Sports Complex, Pune',
            status='ACTIVE',
            description='Regional collegiate tournament.'
        )

        t4 = Tournament.objects.create(
            name='Gujarat Collegiate T20 Trophy',
            sport=cricket,
            start_date=timezone.now().date() - timedelta(days=10),
            end_date=timezone.now().date() + timedelta(days=15),
            location='Indus Cricket Pavilion, Ahmedabad',
            status='ACTIVE',
            description='T20 Championship for collegiate cricket teams.'
        )

        # 6. 10+ Teams across Multiple Cities & Grounds
        teams_data = [
            {
                'name': 'Indus Titans FC', 'code': 'ITFC', 'sport': football, 'coach': coaches[0],
                'color': '#10B981', 'ground': 'Indus Central Field, Ahmedabad (Grass)',
                'wins': 10, 'losses': 2, 'draws': 2
            },
            {
                'name': 'Phoenix Strikers', 'code': 'PHNX', 'sport': football, 'coach': coaches[1],
                'color': '#F59E0B', 'ground': 'Phoenix Turf Dome, Mumbai (Turf)',
                'wins': 9, 'losses': 3, 'draws': 2
            },
            {
                'name': 'Cyber Knights FC', 'code': 'CYBR', 'sport': football, 'coach': coaches[2],
                'color': '#06B6D4', 'ground': 'Silicon Tech Arena, Bangalore (Turf)',
                'wins': 8, 'losses': 4, 'draws': 2
            },
            {
                'name': 'Vanguard Royals', 'code': 'VANG', 'sport': football, 'coach': coaches[3],
                'color': '#EC4899', 'ground': 'Shivaji Sports Complex, Pune (Grass)',
                'wins': 7, 'losses': 5, 'draws': 2
            },
            {
                'name': 'Delhi Dynamos Collegiate', 'code': 'DDCL', 'sport': football, 'coach': coaches[4],
                'color': '#8B5CF6', 'ground': 'Jawaharlal Nehru Arena, New Delhi (Grass)',
                'wins': 6, 'losses': 6, 'draws': 2
            },
            {
                'name': 'Gujarat Gladiators', 'code': 'GGLD', 'sport': football, 'coach': None,
                'color': '#3B82F6', 'ground': 'Gandhinagar Sports City, Gandhinagar (Clay)',
                'wins': 5, 'losses': 7, 'draws': 2
            },
            {
                'name': 'Hyderabad Hawks FC', 'code': 'HYDH', 'sport': football, 'coach': None,
                'color': '#14B8A6', 'ground': 'Gachibowli Stadium, Hyderabad (Turf)',
                'wins': 5, 'losses': 8, 'draws': 1
            },
            {
                'name': 'Chennai Super Strikers', 'code': 'CSS', 'sport': football, 'coach': None,
                'color': '#EAB308', 'ground': 'Jawaharlal Nehru Stadium, Chennai (Grass)',
                'wins': 4, 'losses': 9, 'draws': 1
            },
            {
                'name': 'Kolkata Pioneers FC', 'code': 'KPFC', 'sport': football, 'coach': None,
                'color': '#F43F5E', 'ground': 'Salt Lake Stadium Field 2, Kolkata (Grass)',
                'wins': 4, 'losses': 8, 'draws': 2
            },
            {
                'name': 'Jaipur Royals Club', 'code': 'JRC', 'sport': football, 'coach': None,
                'color': '#A855F7', 'ground': 'Sawai Mansingh Stadium, Jaipur (Grass)',
                'wins': 3, 'losses': 9, 'draws': 2
            },
            {
                'name': 'Indus Royal Challengers', 'code': 'IRC', 'sport': cricket, 'coach': coaches[0],
                'color': '#EF4444', 'ground': 'Indus Cricket Pavilion, Ahmedabad',
                'wins': 5, 'losses': 1, 'draws': 0
            },
            {
                'name': 'Gujarat Titans Cricket', 'code': 'GTC', 'sport': cricket, 'coach': coaches[1],
                'color': '#0284C7', 'ground': 'Narendra Modi Stadium Ground C, Ahmedabad',
                'wins': 4, 'losses': 2, 'draws': 0
            },
        ]

        teams_dict = {}
        for td in teams_data:
            t = Team.objects.create(
                name=td['name'],
                short_code=td['code'],
                sport=td['sport'],
                coach=td['coach'],
                primary_color=td['color'],
                home_ground=td['ground'],
                wins=0,
                losses=0,
                draws=0,
            )
            teams_dict[td['code']] = t

        # Extra clubs so roster, team creation, and history screens feel like a real league.
        extra_teams = [
            ('Ahmedabad United FC','AFCU',football,coaches[2],'#22C55E','Sardar Patel Sports Ground, Ahmedabad'),
            ('Mumbai Mariners','MMAR',football,coaches[3],'#38BDF8','Mumbai University Stadium, Mumbai'),
            ('Bengaluru United','BUNI',football,coaches[4],'#F97316','Bengaluru Sports Village, Bengaluru'),
            ('Pune Athletic Club','PACL',football,None,'#E879F9','Balewadi Sports Complex, Pune'),
            ('Rajasthan Falcons','RAJF',football,None,'#F43F5E','SMS Sports Arena, Jaipur'),
            ('Kerala United Collegiate','KUC',football,None,'#14B8A6','Kochi University Ground, Kochi'),
            ('Indus Women Warriors','IWW',football,coaches[1],'#A78BFA','Indus Women Sports Arena, Ahmedabad'),
            ('Gujarat Strikers Cricket','GSC',cricket,coaches[2],'#60A5FA','Motera Cricket Ground, Ahmedabad'),
            ('Mumbai Mariners Cricket','MMC',cricket,coaches[3],'#FB7185','Mumbai Cricket Academy, Mumbai'),
            ('Indus Hoops','IHOOP',basketball,coaches[4],'#FACC15','Indus Indoor Arena, Ahmedabad'),
            ('Ahmedabad Ballers','ABALL',basketball,None,'#34D399','Sabarmati Indoor Court, Ahmedabad'),
            ('Indus Volley Stars','IVS',volleyball,coaches[0],'#22D3EE','Indus Indoor Arena, Ahmedabad'),
            ('Gujarat Spike Club','GSPK',volleyball,coaches[3],'#A78BFA','Gujarat University Court, Ahmedabad'),
            ('Indus Tennis Collective','ITEN',tennis,coaches[2],'#FACC15','Indus Tennis Centre, Ahmedabad'),
            ('Ahmedabad Racquet Club','ARC',badminton,coaches[4],'#FB7185','Sabarmati Racquet Hall, Ahmedabad'),
        ]
        for name, code, sport_obj, coach_obj, color, ground in extra_teams:
            teams_dict[code] = Team.objects.create(name=name, short_code=code, sport=sport_obj, coach=coach_obj, primary_color=color, home_ground=ground)

        # Give every seeded club a coach so each coach has multiple fixtures available in Matchday Control.
        for idx, team in enumerate(Team.objects.all().order_by('id')):
            if team.coach_id is None:
                team.coach = coaches[idx % len(coaches)]
                team.save(update_fields=['coach'])

        # 7. Seed 80+ Realistically Distributed Players
        players_seed = [
            # Indus Titans FC
            ('Aarav Kapoor', 'ITFC', 'Forward', 7, 98, 'FIT', 9.6, 'Grass', 'Sunny', 94, 96, 92, 14, 13, 7),
            ('Neel Joshi', 'ITFC', 'Midfielder', 8, 96, 'FIT', 9.4, 'Grass', 'Sunny', 92, 88, 95, 14, 6, 11),
            ('Tirth Shah', 'ITFC', 'Midfielder', 10, 95, 'FIT', 9.1, 'Grass', 'Overcast', 90, 89, 94, 13, 5, 9),
            ('Kabir Malhotra', 'ITFC', 'Forward', 9, 92, 'FIT', 8.9, 'Grass', 'Sunny', 89, 93, 86, 14, 9, 4),
            ('Devansh Sharma', 'ITFC', 'Goalkeeper', 1, 98, 'FIT', 9.3, 'Grass', 'Sunny', 88, 78, 96, 14, 0, 2),
            ('Aryan Desai', 'ITFC', 'Defender', 4, 94, 'FIT', 8.6, 'Grass', 'Any', 88, 85, 89, 14, 2, 4),
            ('Jayesh Varma', 'ITFC', 'Defender', 3, 91, 'FIT', 8.4, 'Any', 'Any', 86, 86, 85, 13, 1, 3),
            ('Rohan Mehta', 'ITFC', 'Defender', 5, 90, 'FIT', 8.2, 'Turf', 'Sunny', 85, 83, 86, 12, 2, 3),
            ('Samir Patel', 'ITFC', 'Midfielder', 6, 88, 'FIT', 8.1, 'Turf', 'Humid', 87, 82, 84, 13, 2, 4),
            ('Yashvi Dave', 'ITFC', 'Forward', 11, 89, 'FIT', 8.5, 'Turf', 'Overcast', 88, 90, 82, 12, 5, 3),
            ('Karan Singhal', 'ITFC', 'Defender', 2, 74, 'MINOR_ISSUE', 7.3, 'Grass', 'Rainy', 80, 84, 79, 10, 1, 2),
            ('Harshil Trivedi', 'ITFC', 'Forward', 19, 93, 'FIT', 8.3, 'Grass', 'Sunny', 87, 88, 81, 9, 4, 2),
            ('Pooja Nair', 'ITFC', 'Midfielder', 14, 88, 'FIT', 7.9, 'Clay', 'Rainy', 84, 81, 80, 8, 2, 3),
            ('Parthiv Vyas', 'ITFC', 'Defender', 15, 90, 'FIT', 8.0, 'Turf', 'Windy', 83, 81, 82, 7, 1, 2),
            ('Manan Zala', 'ITFC', 'Goalkeeper', 22, 91, 'FIT', 7.8, 'Any', 'Any', 84, 76, 81, 5, 0, 1),
            ('Dhruv Soni', 'ITFC', 'Forward', 17, 35, 'INJURED', 5.2, 'Grass', 'Sunny', 60, 72, 70, 6, 2, 1),
            ('Aditya Ray', 'ITFC', 'Midfielder', 18, 70, 'MINOR_ISSUE', 6.8, 'Grass', 'Humid', 77, 79, 75, 7, 1, 2),

            # Phoenix Strikers
            ('Julian Alvarez', 'PHNX', 'Forward', 9, 97, 'FIT', 9.5, 'Turf', 'Sunny', 93, 95, 91, 14, 12, 6),
            ('Enzo Fernandez', 'PHNX', 'Midfielder', 8, 96, 'FIT', 9.3, 'Turf', 'Overcast', 92, 88, 93, 14, 5, 9),
            ('Gabriel Martin', 'PHNX', 'Forward', 7, 95, 'FIT', 9.2, 'Turf', 'Sunny', 91, 96, 88, 13, 8, 5),
            ('Lucas Silva', 'PHNX', 'Goalkeeper', 1, 94, 'FIT', 8.9, 'Turf', 'Sunny', 87, 76, 91, 14, 0, 2),
            ('Kai Havertz', 'PHNX', 'Midfielder', 10, 93, 'FIT', 8.8, 'Grass', 'Sunny', 89, 86, 90, 13, 4, 6),
            ('Carlos Diaz', 'PHNX', 'Defender', 5, 92, 'FIT', 8.4, 'Turf', 'Sunny', 87, 84, 86, 13, 2, 4),
            ('Victor Vance', 'PHNX', 'Defender', 3, 91, 'FIT', 8.3, 'Grass', 'Any', 86, 83, 85, 12, 1, 3),
            ('Leo Sterling', 'PHNX', 'Midfielder', 6, 90, 'FIT', 8.2, 'Turf', 'Windy', 88, 85, 84, 11, 2, 4),
            ('Mateo Rossi', 'PHNX', 'Defender', 4, 88, 'FIT', 8.0, 'Turf', 'Rainy', 85, 81, 83, 12, 1, 2),
            ('Marco Asensio', 'PHNX', 'Forward', 11, 87, 'FIT', 8.1, 'Grass', 'Sunny', 85, 89, 83, 10, 3, 3),
            ('David Kim', 'PHNX', 'Defender', 2, 68, 'MINOR_ISSUE', 7.0, 'Clay', 'Humid', 79, 81, 78, 8, 1, 2),
            ('Oliver Twist', 'PHNX', 'Forward', 21, 91, 'FIT', 8.0, 'Turf', 'Sunny', 84, 88, 78, 7, 2, 2),

            # Cyber Knights FC
            ('Rhea Chakraborty', 'CYBR', 'Forward', 10, 96, 'FIT', 9.3, 'Turf', 'Sunny', 92, 94, 90, 14, 10, 5),
            ('Vikramaditya Rao', 'CYBR', 'Midfielder', 8, 93, 'FIT', 8.9, 'Turf', 'Overcast', 90, 86, 92, 13, 4, 8),
            ('Nikhil Nambiar', 'CYBR', 'Defender', 4, 91, 'FIT', 8.5, 'Turf', 'Sunny', 88, 83, 88, 12, 2, 4),
            ('Siddharth Sen', 'CYBR', 'Goalkeeper', 1, 93, 'FIT', 8.7, 'Turf', 'Sunny', 86, 75, 90, 14, 0, 1),
            ('Armaan Malik', 'CYBR', 'Forward', 9, 89, 'FIT', 8.3, 'Grass', 'Sunny', 86, 90, 81, 11, 6, 3),
            ('Zaid Khan', 'CYBR', 'Defender', 3, 88, 'FIT', 8.0, 'Clay', 'Rainy', 84, 81, 82, 12, 1, 3),
            ('Ananya Sharma', 'CYBR', 'Midfielder', 7, 89, 'FIT', 8.2, 'Turf', 'Sunny', 86, 84, 85, 10, 3, 4),

            # Vanguard Royals
            ('Pranav Joshi', 'VANG', 'Forward', 9, 94, 'FIT', 9.1, 'Grass', 'Sunny', 91, 93, 88, 13, 8, 4),
            ('Tanmay Bhatia', 'VANG', 'Midfielder', 7, 91, 'FIT', 8.6, 'Grass', 'Overcast', 89, 85, 88, 12, 3, 6),
            ('Gaurav Kulkarni', 'VANG', 'Defender', 5, 89, 'FIT', 8.2, 'Grass', 'Sunny', 86, 82, 84, 13, 2, 3),
            ('Abhinav Bindra', 'VANG', 'Goalkeeper', 1, 90, 'FIT', 8.4, 'Grass', 'Sunny', 85, 74, 88, 13, 0, 2),
            ('Sushant Patil', 'VANG', 'Defender', 4, 87, 'FIT', 7.9, 'Grass', 'Humid', 83, 80, 82, 11, 1, 3),
            ('Omkar Deshmukh', 'VANG', 'Forward', 11, 88, 'FIT', 8.0, 'Turf', 'Sunny', 85, 87, 80, 9, 4, 3),

            # Delhi Dynamos
            ('Raghav Chadha', 'DDCL', 'Forward', 10, 92, 'FIT', 8.7, 'Grass', 'Sunny', 89, 91, 86, 12, 7, 4),
            ('Kunal Sharma', 'DDCL', 'Midfielder', 8, 89, 'FIT', 8.2, 'Grass', 'Humid', 86, 83, 85, 11, 3, 5),
            ('Mayank Agarwal', 'DDCL', 'Defender', 4, 88, 'FIT', 8.0, 'Grass', 'Sunny', 85, 80, 83, 12, 2, 4),
            ('Jaspreet Singh', 'DDCL', 'Goalkeeper', 1, 89, 'FIT', 8.1, 'Grass', 'Overcast', 84, 75, 86, 12, 0, 1),

            # Gujarat Gladiators
            ('Hardik Raval', 'GGLD', 'Forward', 9, 90, 'FIT', 8.5, 'Clay', 'Sunny', 87, 89, 82, 12, 6, 3),
            ('Chirag Gandhi', 'GGLD', 'Midfielder', 10, 88, 'FIT', 8.1, 'Clay', 'Overcast', 85, 82, 84, 11, 3, 5),
            ('Bhavin Thakkar', 'GGLD', 'Defender', 3, 87, 'FIT', 7.8, 'Clay', 'Sunny', 83, 80, 81, 12, 1, 3),

            # Hyderabad Hawks
            ('Syed Rahim', 'HYDH', 'Forward', 10, 91, 'FIT', 8.6, 'Turf', 'Sunny', 88, 92, 83, 11, 7, 3),
            ('Mohammed Siraj', 'HYDH', 'Defender', 4, 89, 'FIT', 8.1, 'Turf', 'Humid', 85, 81, 84, 12, 2, 3),
            ('Venkatesh Iyer', 'HYDH', 'Midfielder', 8, 88, 'FIT', 8.0, 'Turf', 'Sunny', 84, 83, 83, 10, 3, 4),

            # Chennai Super Strikers
            ('Ravi Ashwin', 'CSS', 'Midfielder', 6, 89, 'FIT', 8.3, 'Grass', 'Humid', 85, 82, 86, 11, 3, 5),
            ('Vijay Shankar', 'CSS', 'Forward', 9, 88, 'FIT', 8.0, 'Grass', 'Rainy', 84, 86, 80, 10, 5, 2),

            # Kolkata Pioneers
            ('Sourav Ganguly', 'KPFC', 'Forward', 10, 90, 'FIT', 8.4, 'Grass', 'Sunny', 86, 88, 85, 10, 6, 4),
            ('Subrata Paul', 'KPFC', 'Goalkeeper', 1, 89, 'FIT', 8.2, 'Grass', 'Rainy', 83, 74, 85, 10, 0, 1),

            # Jaipur Royals
            ('Manish Pandey', 'JRC', 'Forward', 9, 88, 'FIT', 8.1, 'Grass', 'Sunny', 84, 87, 81, 9, 5, 3),

            # Free Agents (Available to sign)
            ('Kushagra Rawat', None, 'Forward', 99, 90, 'FIT', 8.2, 'Any', 'Any', 86, 88, 80, 4, 3, 2),
            ('Sarthak Bansal', None, 'Midfielder', 88, 86, 'FIT', 7.8, 'Grass', 'Sunny', 83, 80, 81, 3, 2, 2),
            ('Tejaswini Sawant', None, 'Defender', 77, 89, 'FIT', 8.0, 'Turf', 'Rainy', 84, 81, 82, 5, 1, 2),
            ('Devendra Jhajharia', None, 'Forward', 55, 92, 'FIT', 8.4, 'Grass', 'Sunny', 88, 89, 84, 6, 4, 3),
        ]

        for p in players_seed:
            team_obj = teams_dict.get(p[1]) if p[1] else None
            Player.objects.create(
                name=p[0],
                team=team_obj,
                sport=football,
                role=p[2],
                jersey_number=p[3],
                fitness_score=p[4],
                injury_status=p[5],
                recent_form=p[6],
                preferred_ground=p[7],
                preferred_weather=p[8],
                stamina_rating=p[9],
                pace_rating=p[10],
                tactical_awareness=p[11],
                matches_played=p[12],
                goals_scored=p[13],
                assists=p[14],
            )

        # Add another 60+ athletes across every club for larger rosters.
        role_map = {'Football':['Goalkeeper','Defender','Midfielder','Forward'], 'Cricket':['Wicketkeeper','Batsman','All-Rounder','Bowler'], 'Basketball':['Guard','Forward','Center'], 'Volleyball':['Setter','Libero','Middle Blocker','Outside Hitter','Opposite'], 'Tennis':['Singles Player'], 'Badminton':['Singles Player','Doubles Player']}
        first_names = ['Aditya','Vihaan','Reyansh','Ishaan','Arjun','Dev','Rohan','Karan','Yash','Manav','Rudra','Ayaan','Krish','Dhruv','Harsh','Samar','Aarush','Mihir','Nivaan','Vivaan']
        last_names = ['Mehta','Shah','Patel','Joshi','Desai','Kapoor','Soni','Trivedi','Rana','Bhatia','Singh','Malhotra','Iyer','Nair','Pillai','Verma']
        generated_index = 0
        for team in teams_dict.values():
            target = 18 if team.sport.name == 'Football' else (15 if team.sport.name == 'Cricket' else (10 if team.sport.name == 'Basketball' else (12 if team.sport.name == 'Volleyball' else 3)))
            for j in range(max(0, target - team.players.count())):
                generated_index += 1
                role = role_map[team.sport.name][j % len(role_map[team.sport.name])]
                Player.objects.create(
                    name=f"{first_names[generated_index % len(first_names)]} {last_names[(generated_index * 3) % len(last_names)]}",
                    jersey_number=20+j, sport=team.sport, team=team, role=role, age=random.randint(18,28),
                    fitness_score=random.randint(76,98), injury_status=random.choices(['FIT','MINOR_ISSUE','INJURED'], weights=[88,9,3])[0],
                    recent_form=round(random.uniform(6.4,9.6),1), preferred_ground=random.choice(['Any','Grass','Turf']),
                    preferred_weather=random.choice(['Any','Sunny','Overcast']), stamina_rating=random.randint(72,96),
                    pace_rating=random.randint(70,96), tactical_awareness=random.randint(70,95), matches_played=random.randint(6,24),
                    goals_scored=random.randint(0,14), assists=random.randint(0,10)
                )

        # Assign a real player owner to seeded clubs where possible so roster management is testable.
        for team in Team.objects.all():
            if not team.owner_id:
                owner = team.players.order_by('created_at','id').first()
                if owner:
                    team.owner = owner
                    team.save(update_fields=['owner'])

        # Link the demo player login to the seeded player profile.
        aarav = Player.objects.filter(name='Aarav Kapoor').first()
        if aarav:
            aarav.user = player_user
            # Keep the demo player as a free agent so the Player Hub can demonstrate Create Team / Join Team.
            aarav.team = None
            aarav.email = player_user.email
            aarav.save(update_fields=['user', 'team', 'email'])
            # Do not leave a seeded team owned by the free-agent demo player.
            titans = teams_dict.get('ITFC')
            if titans and titans.owner_id == aarav.id:
                replacement_owner = titans.players.exclude(id=aarav.id).order_by('created_at','id').first()
                titans.owner = replacement_owner
                titans.save(update_fields=['owner'])

        # 8. Seed 25+ Completed Matches across diverse dates (from 20 days ago to yesterday and today!)
        now = timezone.now()
        completed_fixtures = [
            # Matches from 20 days ago
            (teams_dict['ITFC'], teams_dict['CYBR'], 3, 1, 'Indus Central Field, Ahmedabad', 'Grass', 'Sunny', 20, 16, t1, 'Dominant attacking masterclass by Indus Titans.'),
            (teams_dict['PHNX'], teams_dict['VANG'], 2, 0, 'Phoenix Turf Dome, Mumbai', 'Turf', 'Sunny', 20, 18, t1, 'Clinical counter-attack victory by Phoenix.'),
            
            # Matches from 18 days ago
            (teams_dict['DDCL'], teams_dict['GGLD'], 1, 1, 'Jawaharlal Nehru Arena, New Delhi', 'Grass', 'Overcast', 18, 15, t1, 'Hard-fought tactical stalemate.'),
            (teams_dict['HYDH'], teams_dict['CSS'], 2, 0, 'Gachibowli Stadium, Hyderabad', 'Turf', 'Sunny', 18, 17, t1, 'Clean sheet victory for Hyderabad Hawks.'),
            
            # Matches from 15 days ago
            (teams_dict['ITFC'], teams_dict['HYDH'], 4, 0, 'Indus Central Field, Ahmedabad', 'Grass', 'Sunny', 15, 16, t1, 'Aarav Kapoor hat-trick seals huge 4-0 win.'),
            (teams_dict['KPFC'], teams_dict['JRC'], 2, 1, 'Salt Lake Stadium, Kolkata', 'Grass', 'Rainy', 15, 18, t2, 'Kolkata wins close encounter on wet pitch.'),

            # Matches from 12 days ago
            (teams_dict['CYBR'], teams_dict['PHNX'], 2, 3, 'Silicon Tech Arena, Bangalore', 'Turf', 'Humid', 12, 15, t1, 'Thrilling five-goal thriller in Bangalore.'),
            (teams_dict['VANG'], teams_dict['CSS'], 3, 1, 'Shivaji Sports Complex, Pune', 'Grass', 'Sunny', 12, 17, t1, 'Vanguard Royals dominant second half display.'),

            # Matches from 10 days ago
            (teams_dict['GGLD'], teams_dict['ITFC'], 0, 2, 'Gandhinagar Sports City', 'Clay', 'Sunny', 10, 16, t1, 'Clean sheet triumph on tough clay pitch.'),
            (teams_dict['DDCL'], teams_dict['KPFC'], 2, 2, 'Jawaharlal Nehru Arena, New Delhi', 'Grass', 'Sunny', 10, 18, t2, 'Action-packed 4-goal draw.'),

            # Matches from 8 days ago
            (teams_dict['PHNX'], teams_dict['DDCL'], 3, 1, 'Phoenix Turf Dome, Mumbai', 'Turf', 'Overcast', 8, 16, t1, 'Julian Alvarez brace seals 3 points for Phoenix.'),
            (teams_dict['JRC'], teams_dict['HYDH'], 1, 2, 'Sawai Mansingh Stadium, Jaipur', 'Grass', 'Sunny', 8, 18, t1, 'Hyderabad Hawks secure away victory in Jaipur.'),

            # Matches from 6 days ago
            (teams_dict['CYBR'], teams_dict['VANG'], 1, 1, 'Silicon Tech Arena, Bangalore', 'Turf', 'Rainy', 6, 16, t1, 'Rain-affected physical tactical encounter.'),
            (teams_dict['ITFC'], teams_dict['CSS'], 5, 0, 'Indus Central Field, Ahmedabad', 'Grass', 'Sunny', 6, 19, t1, 'Historic 5-0 goal fest by Indus Titans.'),

            # Matches from 4 days ago
            (teams_dict['HYDH'], teams_dict['PHNX'], 1, 2, 'Gachibowli Stadium, Hyderabad', 'Turf', 'Humid', 4, 16, t1, 'Late 88th-minute winner by Phoenix Strikers.'),
            (teams_dict['GGLD'], teams_dict['KPFC'], 2, 1, 'Gandhinagar Sports City', 'Clay', 'Sunny', 4, 18, t2, 'Gladiators hold onto lead in dying minutes.'),

            # Matches from 2 days ago (Day Before Yesterday)
            (teams_dict['ITFC'], teams_dict['DDCL'], 3, 0, 'Indus Central Field, Ahmedabad', 'Grass', 'Sunny', 2, 16, t1, 'Tactical perfection by Indus Titans with clean sheet.'),
            (teams_dict['VANG'], teams_dict['CYBR'], 2, 1, 'Shivaji Sports Complex, Pune', 'Grass', 'Sunny', 2, 18, t1, 'Pranav Joshi double leads Vanguard Royals to victory.'),

            # Yesterday's Matches
            (teams_dict['PHNX'], teams_dict['GGLD'], 3, 0, 'Phoenix Turf Dome, Mumbai', 'Turf', 'Sunny', 1, 16, t1, 'Phoenix Strikers cruise to victory with fluid wing play.'),
            (teams_dict['CSS'], teams_dict['JRC'], 2, 1, 'Jawaharlal Nehru Stadium, Chennai', 'Grass', 'Humid', 1, 18, t1, 'Chennai Super Strikers claim first victory of tournament.'),

            # Today's Completed Match (Earlier today)
            (teams_dict['VANG'], teams_dict['HYDH'], 2, 0, 'Shivaji Sports Complex, Pune', 'Grass', 'Sunny', 0, 11, t1, 'Morning session shutout win for Vanguard Royals.'),
        ]

        for m_data in completed_fixtures:
            home_t, away_t, h_score, a_score, venue, ground, weather, days_ago, hour, tour, notes = m_data
            winner_t = home_t if h_score > a_score else (away_t if a_score > h_score else None)
            is_draw_val = (h_score == a_score)

            match_time = (now - timedelta(days=days_ago)).replace(hour=hour, minute=0, second=0)

            m = Match.objects.create(
                tournament=tour,
                sport=football,
                home_team=home_t,
                away_team=away_t,
                scheduled_time=match_time,
                venue=venue,
                ground_type=ground,
                weather=weather,
                status='COMPLETED',
                home_score=h_score,
                away_score=a_score,
                winner=winner_t,
                is_draw=is_draw_val,
                summary_notes=notes,
                standings_recorded=True
            )

            # Generate realistic events
            if h_score > 0:
                MatchEvent.objects.create(match=m, minute=random.randint(10, 44), event_type='GOAL', team=home_t, description=f'Goal scored by {home_t.short_code} forward.')
            if a_score > 0:
                MatchEvent.objects.create(match=m, minute=random.randint(46, 85), event_type='GOAL', team=away_t, description=f'Counter-attack finish by {away_t.short_code}.')
            if h_score > 1:
                MatchEvent.objects.create(match=m, minute=random.randint(55, 90), event_type='GOAL', team=home_t, description=f'Set-piece curler by {home_t.short_code}.')
            if (h_score + a_score) > 3:
                MatchEvent.objects.create(match=m, minute=89, event_type='GOAL', team=home_t if h_score > a_score else away_t, description='Breakaway stoppage time goal.')

        # Guarantee a rich archive: every day in the last 45 days has 5 completed matches,
        # with the explicitly curated fixtures above making some days 6.
        football_teams = [t for t in teams_dict.values() if t.sport_id == football.id]
        for day_offset in range(0, 45):
            target_per_day = 5
            match_date = (now - timedelta(days=day_offset)).date()
            existing_count = Match.objects.filter(status='COMPLETED', scheduled_time__date=match_date).count()
            needed = max(0, target_per_day - existing_count)
            for slot in range(needed):
                idx = day_offset * 10 + slot
                home_t = football_teams[idx % len(football_teams)]
                away_t = football_teams[(idx * 3 + slot + 2) % len(football_teams)]
                if home_t.id == away_t.id:
                    away_t = football_teams[(idx * 3 + slot + 3) % len(football_teams)]
                h_score = (idx * 3 + slot + 1) % 5
                a_score = (idx * 5 + slot + 2) % 4
                match_time = (now - timedelta(days=day_offset)).replace(hour=10 + ((slot * 2 + idx) % 10), minute=(slot * 11 + idx) % 60, second=0, microsecond=0)
                winner_t = home_t if h_score > a_score else (away_t if a_score > h_score else None)
                m = Match.objects.create(
                    tournament=t1 if (idx + slot) % 3 else t2, sport=football, home_team=home_t, away_team=away_t,
                    scheduled_time=match_time, venue=home_t.home_ground,
                    ground_type=random.choice(['Grass','Turf','Clay']), weather=random.choice(['Sunny','Overcast','Rainy','Humid']),
                    status='COMPLETED', home_score=h_score, away_score=a_score, winner=winner_t, is_draw=(h_score == a_score),
                    standings_recorded=True, summary_notes=f'Daily league fixture {day_offset + 1}-{slot + 1}: {home_t.name} vs {away_t.name}.'
                )
                for event_idx in range(h_score + a_score):
                    event_team = home_t if event_idx < h_score else away_t
                    roster = list(event_team.players.all())
                    MatchEvent.objects.create(match=m, minute=min(90, 8 + event_idx * 11), event_type='GOAL', team=event_team, player=random.choice(roster) if roster else None, description=f'Goal by {event_team.short_code} in daily league fixture.')

        # Rebuild standings from the completed history so W/L/D totals always match the archive.
        for team in Team.objects.all():
            completed = Match.objects.filter(status='COMPLETED').filter(Q(home_team=team) | Q(away_team=team))
            team.wins = completed.filter(winner=team).count()
            team.draws = completed.filter(is_draw=True).count()
            team.losses = completed.filter(is_draw=False).exclude(winner=team).exclude(winner__isnull=True).count()
            team.save(update_fields=['wins','draws','losses'])

        # Attach realistic player profiles to historical events so match history can show who made the play.
        for event in MatchEvent.objects.filter(player__isnull=True).select_related('team'):
            roster = list(event.team.players.all()) if event.team_id else []
            if roster:
                event.player = random.choice(roster)
                event.save(update_fields=['player'])

        # 9. Create 3 Active LIVE Matches (Happening right now!)
        m_live1 = Match.objects.create(
            tournament=t1,
            sport=football,
            home_team=teams_dict['ITFC'],
            away_team=teams_dict['PHNX'],
            scheduled_time=now - timedelta(minutes=62),
            venue='Indus Central Stadium Arena, Ahmedabad',
            ground_type='Grass',
            weather='Sunny',
            status='LIVE',
            home_score=2,
            away_score=1,
            summary_notes='Top-of-the-table championship title clash currently in the second half.'
        )
        MatchEvent.objects.create(match=m_live1, minute=14, event_type='GOAL', team=teams_dict['ITFC'], description='Aarav Kapoor strikes from outside the penalty area.')
        MatchEvent.objects.create(match=m_live1, minute=31, event_type='GOAL', team=teams_dict['PHNX'], description='Julian Alvarez levels the score with a diving header.')
        MatchEvent.objects.create(match=m_live1, minute=48, event_type='GOAL', team=teams_dict['ITFC'], description='Neel Joshi half-volley into the top corner.')
        MatchEvent.objects.create(match=m_live1, minute=55, event_type='YELLOW_CARD', team=teams_dict['PHNX'], description='Tactical shirt pull to halt breakaway.')

        m_live2 = Match.objects.create(
            tournament=t2,
            sport=football,
            home_team=teams_dict['CYBR'],
            away_team=teams_dict['DDCL'],
            scheduled_time=now - timedelta(minutes=25),
            venue='Salt Lake Sports Complex, Kolkata',
            ground_type='Turf',
            weather='Overcast',
            status='LIVE',
            home_score=1,
            away_score=0,
            summary_notes='Super Cup Knockout Quarter-Final in the 1st half.'
        )
        MatchEvent.objects.create(match=m_live2, minute=18, event_type='GOAL', team=teams_dict['CYBR'], description='Rhea Chakraborty penalty kick conversion.')

        m_live3 = Match.objects.create(
            tournament=t1,
            sport=football,
            home_team=teams_dict['GGLD'],
            away_team=teams_dict['CSS'],
            scheduled_time=now - timedelta(minutes=40),
            venue='Gandhinagar Sports City Arena',
            ground_type='Clay',
            weather='Sunny',
            status='LIVE',
            home_score=0,
            away_score=0,
            summary_notes='Defensive tactical battle in Gandhinagar.'
        )

        # 10. Create 12+ Upcoming Scheduled Matches across various locations and dates
        upcoming_fixtures = [
            (teams_dict['ITFC'], teams_dict['VANG'], 'Indus Central Field, Ahmedabad', 'Grass', 'Rainy', 1, 16, t1),
            (teams_dict['PHNX'], teams_dict['CYBR'], 'Phoenix Turf Dome, Mumbai', 'Turf', 'Sunny', 2, 18, t1),
            (teams_dict['CYBR'], teams_dict['CSS'], 'Silicon Tech Arena, Bangalore', 'Turf', 'Windy', 3, 15, t1),
            (teams_dict['DDCL'], teams_dict['HYDH'], 'Jawaharlal Nehru Arena, New Delhi', 'Grass', 'Sunny', 4, 17, t1),
            (teams_dict['VANG'], teams_dict['ITFC'], 'Shivaji Sports Complex, Pune', 'Grass', 'Overcast', 5, 19, t1),
            (teams_dict['GGLD'], teams_dict['CYBR'], 'Gandhinagar Sports City Arena', 'Clay', 'Humid', 6, 16, t1),
            (teams_dict['CSS'], teams_dict['PHNX'], 'Jawaharlal Nehru Stadium, Chennai', 'Grass', 'Rainy', 7, 18, t1),
            (teams_dict['HYDH'], teams_dict['ITFC'], 'Gachibowli Stadium, Hyderabad', 'Turf', 'Sunny', 8, 20, t1),
            (teams_dict['KPFC'], teams_dict['VANG'], 'Salt Lake Stadium, Kolkata', 'Grass', 'Sunny', 10, 16, t2),
            (teams_dict['JRC'], teams_dict['DDCL'], 'Sawai Mansingh Stadium, Jaipur', 'Grass', 'Sunny', 12, 17, t1),
            (teams_dict['ITFC'], teams_dict['KPFC'], 'Indus Central Field, Ahmedabad', 'Grass', 'Sunny', 14, 16, t2),
            (teams_dict['PHNX'], teams_dict['JRC'], 'Phoenix Turf Dome, Mumbai', 'Turf', 'Sunny', 15, 18, t1),
            (teams_dict['IRC'], teams_dict['GTC'], 'Indus Cricket Pavilion, Ahmedabad', 'Grass', 'Sunny', 2, 11, t4),
            (teams_dict['GTC'], teams_dict['GSC'], 'Motera Cricket Ground, Ahmedabad', 'Grass', 'Overcast', 4, 14, t4),
            (teams_dict['IHOOP'], teams_dict['ABALL'], 'Indus Indoor Arena, Ahmedabad', 'Indoor', 'Overcast', 3, 18, None),
            (teams_dict['IVS'], teams_dict['GSPK'], 'Indus Indoor Arena, Ahmedabad', 'Indoor', 'Sunny', 6, 17, None),
        ]

        for u_data in upcoming_fixtures:
            home_t, away_t, venue, ground, weather, days_ahead, hour, tour = u_data
            Match.objects.create(
                tournament=tour,
                sport=home_t.sport,
                home_team=home_t,
                away_team=away_t,
                scheduled_time=now + timedelta(days=days_ahead, hours=hour),
                venue=venue,
                ground_type=ground,
                weather=weather,
                status='SCHEDULED',
                summary_notes=f'Upcoming fixture between {home_t.name} and {away_t.name}. Surface: {ground}, Forecast: {weather}.'
            )

        # Extra matchday fixtures ensure every seeded coach has several fixtures
        # available in the Coach Matchday and Admin Override screens.
        coach_pairs = [
            ('ITFC','MMAR',2,15,t1), ('PHNX','BUNI',3,17,t1),
            ('CYBR','PACL',4,16,t1), ('VANG','RAJF',5,18,t1),
            ('DDCL','KUC',6,17,t1), ('IRC','GTC',3,12,t4),
            ('IHOOP','ABALL',5,18,None), ('IVS','GSPK',7,17,None),
        ]
        for home_code, away_code, days_ahead, hour, tour in coach_pairs:
            home_t, away_t = teams_dict[home_code], teams_dict[away_code]
            Match.objects.create(
                tournament=tour,
                sport=home_t.sport,
                home_team=home_t,
                away_team=away_t,
                scheduled_time=now + timedelta(days=days_ahead, hours=hour),
                venue=home_t.home_ground,
                ground_type='Indoor' if home_t.sport.name in ['Basketball','Volleyball'] else ('Turf' if home_t.sport.name == 'Football' else 'Grass'),
                weather='Overcast',
                status='SCHEDULED',
                summary_notes=f'Matchday fixture: {home_t.name} vs {away_t.name}.'
            )

        # 11. Seed Audit Logs for Coach Overrides (SRS FR-6.6, FR-6.7)
        p_out = Player.objects.filter(name='Dhruv Soni').first()
        p_in = Player.objects.filter(name='Harshil Trivedi').first()
        if p_out and p_in:
            CoachOverrideLog.objects.create(
                match=m_live1,
                coach=coaches[0],
                action_type='SUBSTITUTION',
                outgoing_player=p_out,
                incoming_player=p_in,
                reason='Acute hamstring tightness reported during matchday warmup. Instant medical substitution executed.',
                timestamp=now - timedelta(minutes=75),
                ai_recalculated=True
            )

        CoachOverrideLog.objects.create(
            match=m_live1,
            coach=coaches[0],
            action_type='VENUE_CHANGE',
            old_venue='Indus Practice Pitch 3',
            new_venue='Indus Central Stadium Arena, Ahmedabad (Grass)',
            reason='Unscheduled waterlogging on practice turf due to sudden thunderstorm. Match upgraded to central stadium.',
            timestamp=now - timedelta(hours=3),
            ai_recalculated=True
        )

        # 12. Pre-generate AI Log for Titans
        titans_players = list(teams_dict['ITFC'].players.all())
        rec = AIRecEngine.recommend_lineup(titans_players, 'Football', 'Grass', 'Sunny')
        AILineupLog.objects.create(
            match=m_live1,
            team=teams_dict['ITFC'],
            confidence_percentage=rec['overall_confidence'],
            weather_condition='Sunny',
            ground_type='Grass',
            lineup_json=json.dumps(rec['starting_xi']),
            factors_summary_json=json.dumps(rec['factors'])
        )

        self.stdout.write(self.style.SUCCESS("SportsHub database seeded with 23+ teams, 140+ players, 75+ completed date-wise matches, 3 live fixtures, and 12 upcoming matches!"))
