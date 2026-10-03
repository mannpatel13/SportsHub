# SportsHub Fixed v4 — Dashboard & Matchday Repair

Django sports management application with role-based admin/coach/player workflows.

## One-command Windows setup + run (PowerShell)

Open a terminal in this folder and run:

```powershell
python -m venv venv; .\venv\Scripts\python.exe -m pip install -r requirements.txt; .\venv\Scripts\python.exe manage.py migrate; .\venv\Scripts\python.exe manage.py seed_data; .\venv\Scripts\python.exe manage.py runserver
```

Then open http://127.0.0.1:8000/ .

If the virtual environment and packages are already installed:

```powershell
.\venv\Scripts\python.exe manage.py migrate; .\venv\Scripts\python.exe manage.py seed_data; .\venv\Scripts\python.exe manage.py runserver
```

## Main fixes in v4

- Sport-specific squad sizing for player-created teams.
- Player can create or join a team; Create/Join controls disappear while already in a team.
- Team owner can manage the roster: add, edit, and remove player profiles with name + Gmail/email; created-team profiles appear immediately in the roster.
- Registered accounts can be linked to team profiles by email.
- Player email is stored on the athlete profile.
- Match archive is seeded with 5 completed fixtures per day across the previous 45 days, with player-linked match events.
- Coach Matchday is hidden from player accounts and the old Audit Trail UI has been removed from navigation.
- Coach/admin Matchday shows many scheduled/live fixtures across managed teams and sports, with robust fallback data for legacy databases.
- Substitution and venue override workflows retain role/roster validation and AI re-evaluation.
- Admin and Coach dashboards now render their full content; dashboard/report charts also include a no-JavaScript fallback.
- Reports and Match History use server-generated landscape A4 PDFs with readable tables and consistent colors.

## Demo accounts

- Admin: `admin` / `admin123`
- Coach: `coach_mann` / `coach123`
- Player: `player_aarav` / `player123`

The demo player starts as a football free agent so the Player Hub can demonstrate Create Team and Join Team.

> `seed_data` resets the demo database. Do not run it after entering data you want to keep.


## Important

`seed_data` creates a fresh demo dataset with 20+ teams, a large multi-sport player roster, 5+ completed matches per day across the archive, live matches, and many upcoming fixtures so Coach Matchday and Admin Override are populated.
