from django.db import migrations, models
import django.db.models.deletion


def assign_existing_team_owners(apps, schema_editor):
    Team = apps.get_model('core', 'Team')
    Player = apps.get_model('core', 'Player')
    for team in Team.objects.all():
        first_player = Player.objects.filter(team_id=team.id).order_by('created_at', 'id').first()
        if first_player:
            Team.objects.filter(pk=team.pk).update(owner_id=first_player.id)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0004_teaminvitation'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='team',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='owned_teams', to='core.player'),
        ),
        migrations.RunPython(assign_existing_team_owners, migrations.RunPython.noop),
    ]
