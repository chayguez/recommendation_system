import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spotify.settings')

app = Celery('spotify')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Set the concurrency level for Celery workers
# app.conf.worker_concurrency = 1  # Change this to your desired concurrency level


app.conf.beat_schedule = {
    # Other tasks (if any)...
    'run-community-optimizer-for-all-logged-in_users': {
        'task': 'accounts.tasks.run_community_optimizer_for_all_logged_in_users',
        'schedule': timedelta(minutes=1),  # Run the task every 10 minutes, adjust this as needed
        'options': {'concurrency': 1},  # Set concurrency level to 1
    },
    'run-suggested-songs-fetching-for-all-logged-in-users': {
        'task': 'accounts.tasks.run_suggested_songs_fetching_for_all_logged_in_users',
        'schedule': timedelta(minutes=1440),  # Run the task every 24 hours, adjust this as needed
        'options': {'concurrency': 1},  # Set concurrency level to 1
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')