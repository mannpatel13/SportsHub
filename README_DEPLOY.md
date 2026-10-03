# SportsHub — Free Deployment

This project is configured for deployment as a Django web service on Render.

## Local development

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Deploy

1. Push this folder to a GitHub repository.
2. Create a free PostgreSQL database on a provider such as Neon.
3. Copy the database provider's PostgreSQL connection string (`DATABASE_URL`).
4. In Render, create a new Web Service and connect the GitHub repository.
5. Render can use the included `render.yaml`, or configure:
   - Build Command: `./build.sh`
   - Start Command: `python -m gunicorn sportshub_project.wsgi:application --workers 2 --timeout 120`
6. Set these environment variables in Render:
   - `SECRET_KEY`: Generate a secure value.
   - `DJANGO_DEBUG`: `False`
   - `DATABASE_URL`: your PostgreSQL connection string.
   - `ALLOWED_HOSTS`: your Render hostname, e.g. `sportshub-xxxx.onrender.com`
7. Deploy.
8. Open Render Shell and optionally run:

```bash
python manage.py createsuperuser
python manage.py seed_data
```

The `seed_data` command is included in the original project and can populate the demo data.
