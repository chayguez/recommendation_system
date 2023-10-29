from __future__ import absolute_import, unicode_literals
from celery import shared_task
from .Community import community_optimizer, suggestion_songs_fetching
from threading import Thread, Lock, get_ident
from django.core.cache import cache
from django.contrib.auth import get_user_model,login
from .utils import get_logged_in_users

User = get_user_model()
recently_logged_users = []

"""----------------------------- 1. Community Optimizer Tasks -----------------------------"""


@shared_task
def run_community_optimizer_for_all_logged_in_users():
    global recently_logged_users
    logged_in_users = get_logged_in_users()
    for user in logged_in_users:
        if user not in recently_logged_users:
            recently_logged_users.append(user)
    print("logged in users :", logged_in_users)
    print("recently logged users :", recently_logged_users)
    run_community_optimizer_for_logged_in_users(recently_logged_users)


def run_community_optimizer_for_logged_in_users(logged_in_users):
    threads = []
    for user in logged_in_users:
        client_id = user.username  # or however you access the user's client_id
        t = Thread(target=run_community_optimizer, args=(client_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


@shared_task
def run_community_optimizer(client_id):
    # Set the task_running flag
    print('run_community_optimizer running with id', client_id)
    task_running_key = f'task_running_{client_id}'
    cache.set(task_running_key, True, None)

    community_optimizer(client_id)

    # Unset the task_running flag
    cache.delete(task_running_key)


"""----------------------------- 2. Suggested Songs Fetching Tasks  -----------------------------"""


@shared_task()
def run_suggested_songs_fetching_for_all_logged_in_users():
    global recently_logged_users
    logged_in_users = get_logged_in_users()
    for user in logged_in_users:
        if user not in recently_logged_users:
            recently_logged_users.append(user)
    print("logged in users :", logged_in_users)
    print("recently logged users :", recently_logged_users)
    run_suggested_songs_fetching_for_logged_in_users(recently_logged_users)


def run_suggested_songs_fetching_for_logged_in_users(logged_in_users):
    threads = []
    for user in logged_in_users:
        client_id = user.username  # or however you access the user's client_id
        t = Thread(target=run_suggested_songs_fetching, args=(client_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


@shared_task
def run_suggested_songs_fetching(client_id):
    # Set the task_running flag
    print('suggested_songs_fetching running with id', client_id)
    task_running_key = f'task_running_{client_id}'
    cache.set(task_running_key, True, None)

    suggestions = suggestion_songs_fetching(client_id)
    cache_key = f'user_suggestions_{client_id}'
    cache.set(cache_key, suggestions, 3600)  # Store the suggestions for 1 hour, adjust the duration as needed

    # Unset the task_running flag
    cache.delete(task_running_key)