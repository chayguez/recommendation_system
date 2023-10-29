import threading
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.utils import timezone

_thread_locals = threading.local()

def set_current_request(request):
    _thread_locals.current_request = request

def get_current_request():
    return getattr(_thread_locals, 'current_request', None)


User = get_user_model()

def get_logged_in_users():
    logged_in_users = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()):
        user_id = session.get_decoded().get('_auth_user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            if user not in logged_in_users:
                logged_in_users.append(user)
    return logged_in_users
