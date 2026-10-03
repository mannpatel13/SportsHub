from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_player_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='match',
            name='standings_recorded',
            field=models.BooleanField(
                default=False,
                help_text='Whether this match result has been included in team W/L/D totals.',
            ),
        ),
    ]
