from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Sport, Coach, Team, Player, Tournament, Match, CoachOverrideLog

class SportsHubFeatureTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser('testadmin','test@example.com','admin12345')
        self.coach_user=User.objects.create_user('testcoach',password='coach12345')
        self.coach=Coach.objects.create(user=self.coach_user,full_name='Test Coach')
        self.sport=Sport.objects.create(name='Football',code='FB')
        self.tournament=Tournament.objects.create(name='Test Cup',sport=self.sport)
        self.home=Team.objects.create(name='Home FC',short_code='HFC',sport=self.sport,coach=self.coach)
        self.away=Team.objects.create(name='Away FC',short_code='AFC',sport=self.sport)
        for i in range(13): Player.objects.create(name=f'Player {i}',jersey_number=i+1,sport=self.sport,team=self.home,role='Forward')
        self.match=Match.objects.create(home_team=self.home,away_team=self.away,sport=self.sport,tournament=self.tournament,scheduled_time=timezone.now()+timedelta(hours=2))
    def test_player_add(self):
        self.client.force_login(self.admin); r=self.client.post(reverse('player_add'),{'name':'New Player','sport':self.sport.id,'team':self.home.id,'role':'Forward','jersey_number':99,'age':21,'fitness_score':90,'recent_form':8.5,'injury_status':'FIT','preferred_ground':'Any','preferred_weather':'Any'}); self.assertEqual(r.status_code,302); self.assertTrue(Player.objects.filter(name='New Player').exists())
    def test_team_add(self):
        self.client.force_login(self.admin); r=self.client.post(reverse('team_add'),{'name':'New FC','short_code':'NFC','sport':self.sport.id,'coach':self.coach.id,'home_ground':'Arena','primary_color':'#10B981'}); self.assertEqual(r.status_code,302); self.assertTrue(Team.objects.filter(short_code='NFC').exists())
    def test_match_schedule(self):
        self.client.force_login(self.admin); dt=(timezone.now()+timedelta(days=1)).strftime('%Y-%m-%dT%H:%M'); r=self.client.post(reverse('match_schedule'),{'home_team':self.home.id,'away_team':self.away.id,'tournament':self.tournament.id,'scheduled_time':dt,'venue':'Test Arena','ground_type':'Grass','weather':'Sunny'}); self.assertEqual(r.status_code,302); self.assertTrue(Match.objects.filter(venue='Test Arena').exists())
    def test_substitution(self):
        self.client.force_login(self.coach_user); out=Player.objects.filter(team=self.home).first(); incoming=Player.objects.filter(team=self.home).last(); r=self.client.post(reverse('api_coach_substitute'),data='{"match_id":%d,"outgoing_player_id":%d,"incoming_player_id":%d,"reason":"Injury during warmup"}'%(self.match.id,out.id,incoming.id),content_type='application/json'); self.assertEqual(r.status_code,200); self.assertEqual(r.json()['status'],'success'); out.refresh_from_db(); self.assertFalse(out.is_available_for_matchday); self.assertTrue(CoachOverrideLog.objects.filter(match=self.match,action_type='SUBSTITUTION').exists())
