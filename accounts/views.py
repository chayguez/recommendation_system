from django.shortcuts import redirect,render,HttpResponse,HttpResponseRedirect
import requests
from django.contrib.auth import get_user_model,login
from django.contrib.auth import logout
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse
import base64
from django.views.decorators.http import require_GET
from django.core.cache import cache
from django.urls import reverse
from django.db import connections
from .Community import Community
from celery.utils.log import get_task_logger


User = get_user_model()
logger = get_task_logger(__name__)


@csrf_exempt
def get_access_token(request):
    # Set up the authorization header
    client_id = settings.SPOTIFY_CLIENT_ID
    client_secret = settings.SPOTIFY_CLIENT_SECRET
    credentials = f"{client_id}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode("ascii")).decode("ascii")
    headers = {"Authorization": f"Basic {encoded_credentials}"}

    # Get the authorization code from the request
    code = request.POST.get("code", None)

    # Make a request to get the access token
    if code:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.SPOTIFY_REDIRECT_URI,
        }
        response = requests.post("https://accounts.spotify.com/api/token", data=data, headers=headers)
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({"error": "Failed to get access token."}, status=400)
    else:
        return JsonResponse({"error": "No authorization code provided."}, status=400)


@require_GET
def get_song_details(request, song_id):
    # get the song_id parameter from the GET request
    # song_id = request.GET.get('song_id')
    # make a request to the Spotify API to get the song details
    headers = {
        'Authorization': f'Bearer {request.session.get("spotify_access_token")}',
        'Content-Type': 'application/json'
    }
    response = requests.get(f'https://api.spotify.com/v1/tracks/{song_id}', headers=headers)

    # check if the request was successful and return the song details in a JSON response
    if response.status_code == 200:
        song_details = response.json()
        response_data = {
            'name': song_details['name'],
            'artist': song_details['artists'][0]['name'],
            'preview_url': song_details['preview_url']
        }
        return JsonResponse(response_data)
    else:
        print(response.text)
        return JsonResponse({'error': 'Failed to get song details.'}, status=500)


def spotify_login(request):
    client_id = "8b5a7a681e2e417a995d69768422348a"
    redirect_uri = "http://127.0.0.1:8000/callback/"
    scope = "user-library-read"
    auth_url = f"https://accounts.spotify.com/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(auth_url)
# Create your views here.


def custom_logout(request):
    logout(request)
    return redirect('home')


def refresh_access_token(refresh_token, client_id, client_secret):
    token_url = "https://accounts.spotify.com/api/token"
    response = requests.post(token_url, data={
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    response_data = response.json()
    new_access_token = response_data.get("access_token")
    return new_access_token


def spotify_callback(request):
    client_id = "8b5a7a681e2e417a995d69768422348a"
    client_secret = "90fd717929e2441c91781fd6e0657964"
    redirect_uri = "http://127.0.0.1:8000/callback/"
    code = request.GET.get("code")
    token_url = "https://accounts.spotify.com/api/token"
    response = requests.post(token_url, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
    })
    response_data = response.json()
    print(response_data)
    access_token = response_data.get("access_token")
    refresh_token = response_data.get("refresh_token")
    request.session["spotify_access_token"] = access_token
    request.session["spotify_refresh_token"] = refresh_token

    headers = {
            "Authorization": f"Bearer {access_token}"
        }
    profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)

    # Check if the status code is not 200 (HTTP OK)
    if profile_response.status_code != 200:
        print(f"Error: status code {profile_response.status_code}")
        print(profile_response.text)

    # Check if the status code is 401 (Unauthorized)
    if profile_response.status_code == 401:
        print("Refreshing access token")
        refresh_token = request.session.get("spotify_refresh_token")
        access_token = refresh_access_token(refresh_token, client_id, client_secret)
        request.session["spotify_access_token"] = access_token
        headers["Authorization"] = f"Bearer {access_token}"
        profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)

    profile_data = profile_response.json()
    spotify_user_id = profile_data.get("id")
    # Create a new user with the Spotify user ID as the username
    try:
            user = User.objects.get(username=spotify_user_id)
            # muzuser =Users.objects.using('muz').get(user_id=spotify_user_id)
            # Log in the user
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
    except User.DoesNotExist:
            # Create a new user with the Spotify user ID as the username
            user = User.objects.create_user(username=spotify_user_id, email='', password=None)
            # muz_user = Users(user_id=user.id)
            # # Save the `Users` object to the `muz` database
            # muz_user.save(using='muz')
            user.spotify_access_token = access_token
            user.spotify_refresh_token = refresh_token
            user.save()
            # Log in the user
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
    # Check if the user exists in the `muz` database
    with connections['muz'].cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users WHERE user_id = %s", [spotify_user_id])
        result = cursor.fetchone()

        # If the user does not exist in the `muz` database, add it
        if not result:
            cursor.execute("INSERT INTO Users (user_id) VALUES (%s)", [spotify_user_id])

    # Get the user's playlists from the Spotify API
    playlists_url = "https://api.spotify.com/v1/me/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # playlists_response = requests.get(playlists_url, headers=headers)
    # playlists_data = playlists_response.json()
    playlists_data = {"items": fetch_all_items(playlists_url, headers)}
    # Iterate over the playlists and add them to the `Playlists` model in the `muz` database
    for playlist in playlists_data.get("items", []):
        playlist_id = playlist.get("id")
        with connections['muz'].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Playlists WHERE playlist_id = %s AND user_id = %s", [playlist_id, spotify_user_id])
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("INSERT INTO Playlists (playlist_id, user_id) VALUES (%s, %s)", [playlist_id, spotify_user_id])

        # Get the songs in the playlist from the Spotify API
        playlist_songs_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        playlist_songs_response = requests.get(playlist_songs_url, headers=headers)
        playlist_songs_data = playlist_songs_response.json()

        # Iterate over the songs and add them to the `Songs` and `SongsPlaylists` models in the `muz` database
        for track in playlist_songs_data.get("items", []):
            song_id = track.get("track", {}).get("id")
            with connections['muz'].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM Songs WHERE song_id = %s", [song_id])
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute("INSERT INTO Songs (song_id) VALUES (%s)", [song_id])
                
                cursor.execute("SELECT COUNT(*) FROM songs_playlists WHERE song_id = %s AND playlist_id = %s", [song_id, playlist_id])
                count = cursor.fetchone()[0]
                if count == 0:
                    cursor.execute("INSERT INTO songs_playlists (song_id, playlist_id) VALUES (%s, %s)", [song_id, playlist_id])

    # Create a new playlist for the logged-in user named `liked_songs_{spotify_user_id}`
    liked_songs_playlist_id = f"liked_songs_{spotify_user_id}"
    with connections['muz'].cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM Playlists WHERE playlist_id = %s AND user_id = %s", [liked_songs_playlist_id, spotify_user_id])
        count = cursor.fetchone()[0]
        if count == 0:
            cursor.execute("INSERT INTO Playlists (playlist_id, user_id) VALUES (%s, %s)", [liked_songs_playlist_id, spotify_user_id])

    # Get the liked songs from the liked songs playlist
    liked_songs_url = "https://api.spotify.com/v1/me/tracks"
    # liked_songs_response = requests.get(liked_songs_url, headers=headers)
    # liked_songs_data = liked_songs_response.json()
    liked_songs_data = {"items": fetch_all_items(liked_songs_url, headers)}

    # Iterate over the liked songs and add them to the `Songs` and `SongsPlaylists` models in the `muz` database
    for track in liked_songs_data.get("items", []):
        song_id = track.get("track", {}).get("id")
        #print(song_id)
        with connections['muz'].cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Songs WHERE song_id = %s", [song_id])
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("INSERT INTO Songs (song_id) VALUES (%s)", [song_id])

            cursor.execute("SELECT COUNT(*) FROM songs_playlists WHERE song_id = %s AND playlist_id = %s", [song_id, liked_songs_playlist_id])
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("INSERT INTO songs_playlists (song_id, playlist_id) VALUES (%s, %s)", [song_id, liked_songs_playlist_id])

    # Redirect the user to the tracks page
    request.session["spotify_access_token"] = access_token
    request.session.modified = True    # Redirect the user to the tracks page
    return redirect("user_tracks")


def get_user_tracks(request):
    access_token = request.session.get("spotify_access_token")
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me/tracks", headers=headers)
    response_data = response.json()
    tracks = response_data.get("items")
    # users = Playlists.objects.using('muz').all()
    # print(users)
    # Process the user's tracks and render a template
    return render(request, "tracks.html", {"tracks": tracks})


def home(request):
    if request.user.is_authenticated and request.session.get("spotify_access_token"):
        return redirect("user_tracks")
    else:
        return render(request, "login.html")


def suggestions_view(request):
    access_token = request.session.get("spotify_access_token")
    songs_suggestion = request.session.get("songs_suggestion")
    task_running = request.session.get("update_songs_suggestion_running", False)   
    desired_suggestions_count = 10  # Set this to the number of user suggestions you want to display

    if request.method == 'POST':
        return HttpResponseRedirect(reverse('suggestions'))

    else:
        access_token = request.session.get("spotify_access_token")
        client_id = request.user.username
        print(client_id)
        cache_key = f'user_suggestions_{client_id}'
        task_running_key = f'task_running_{client_id}'

        songs_suggestion = cache.get(cache_key)
        task_running = cache.get(task_running_key)
        print(cache_key)
        if not songs_suggestion and not task_running:
            community_instance = Community(client_id)
            community_instance.load_community_from_database()
            suggestions = community_instance.get_suggestions()

            cache_key = f'user_suggestions_{client_id}'
            cache.set(cache_key, suggestions, 3600)  # Store the suggestions for 1 hour, adjust the duration as needed

        context = {
            'songs_suggestion': songs_suggestion if songs_suggestion else [],
            'access_token': access_token,
        }
        return render(request, 'songs_suggestions.html', context)


@csrf_exempt
def like_dislike_song(request):
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        liked = request.POST.get('liked') == 'true'  # Convert the string 'true'/'false' to a boolean
        
        client_id = request.user.username # Replace this line with the correct way to get the client_id
        print('LIKE_DISLIKE_SONG:', song_id)
        community_instance = Community(client_id)
        community_instance.load_community_from_database()
        community_instance.feedback_refiner(song_id, liked)
        community_instance.save_community_to_database()

        return JsonResponse({'status': 'ok'})
    else:
        return JsonResponse({'status': 'error', 'error': 'Invalid request method'})


def check_task_status(request):
    client_id = request.user.username

    cache_key = f'user_suggestions_{client_id}'
    task_running_key = f'task_running_{client_id}'

    task_running = cache.get(task_running_key)
    songs_suggestion = cache.get(cache_key)

    if task_running:
        return JsonResponse({'status': 'running'})
    else:
        return JsonResponse({'status': 'complete', 'data': songs_suggestion})


def chart(request):

    return render(request, 'chart.html')


def fetch_all_items(url, headers):
    items = []
    limit = 50
    offset = 0
    while True:
        response = requests.get(url, headers=headers, params={"limit": limit, "offset": offset})
        data = response.json()
        items.extend(data.get("items", []))
        if len(data.get("items", [])) < limit:
            break
        offset += limit
    return items
