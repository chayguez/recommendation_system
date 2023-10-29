from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('',views.home,name='home'),
    path('login/', views.spotify_login, name='spotify_login'),
    path('callback/', views.spotify_callback, name='spotify_callback'),
    path('tracks/', views.get_user_tracks, name='user_tracks'),
    path('logout/', views.custom_logout, name='logout'),
    path('suggestions/', views.suggestions_view, name='suggestions'),
    path('get-access-token//', views.get_access_token, name='get_access_token'),
    path('get-song-details/<str:song_id>/', views.get_song_details, name='get_song_details'),
    path('check_task_status/', views.check_task_status, name='check_task_status'),
    path('chart/', views.chart, name='chart'),
    path('like_dislike_song/', views.like_dislike_song, name='like_dislike_song'),
    # path('last_update_time/', views.last_update_time, name='last_update_time'),
]
