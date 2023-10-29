from .Database import DataBase
import pickle
import random
import numpy as np


class Client:

    def __init__(self, id):
        self.liked_songs = []
        self.playlists_songs = {}
        self.num_total_songs = 0
        self.num_total_songs_w_duplicates = 0
        self.num_total_songs_w_liked_songs = 0
        self.id = id
        self.database = DataBase()
        self.songs_playlists_duplicate_in_user = {}
        random.seed(10)
        self.init()

    def init(self):
        playlists_id = self.database.get_user_playlists(self.id)
        dup_songs_in_user = self.database.get_dup_songs_in_user(self.id)
        # store the songs duplicates that exists in the user itself :
        for song_playlist in dup_songs_in_user:
            if song_playlist[0] in self.songs_playlists_duplicate_in_user:
                self.songs_playlists_duplicate_in_user[song_playlist[0]].append(song_playlist[1])
            else:
                self.songs_playlists_duplicate_in_user[song_playlist[0]] = [song_playlist[1]]

        songs_to_remove = []
        for song, playlists_list in self.songs_playlists_duplicate_in_user.items():
            for playlist in playlists_list:
                if playlist[:11] == 'liked_songs':
                    playlists_list.remove(playlist)
                    if len(playlists_list) == 1:
                        songs_to_remove.append(song)

        for song in songs_to_remove:
            del self.songs_playlists_duplicate_in_user[song]

        for playlist_id in playlists_id:
            self.add_per_playlist_new(playlist_id[0])

        self.split_inner_duplicates_new()
        self.init_num_songs_new()

    def add_per_playlist_new(self, playlist_id):
        playlist_songs_brut = self.database.get_playlist_songs(playlist_id)
        playlist_songs = [x for (x,) in playlist_songs_brut]
        if playlist_id[:11] == 'liked_songs':
            self.liked_songs = playlist_songs
        else:
            self.playlists_songs[playlist_id] = playlist_songs

    def split_inner_duplicates_new(self):
        for song, playlists in self.songs_playlists_duplicate_in_user.items():
            chosen_playlist = random.sample(playlists, 1)[0]
            for playlist in playlists:
                if playlist != chosen_playlist:
                    self.playlists_songs[playlist].remove(song)

    def init_num_songs_new(self):
        songs_w_dup = []
        for songs in self.playlists_songs.values():
            songs_w_dup.extend(songs)
        self.num_total_songs = len(set(songs_w_dup))
        songs_w_dup.extend(self.liked_songs)
        self.num_total_songs_w_liked_songs = len(set(songs_w_dup))

    def get_playlists_id_new(self):
        playlists = self.playlists_songs.keys()
        return playlists

    def get_playlist_songs(self, playlist_id):
        playlist_songs = self.playlists_songs[playlist_id]
        return playlist_songs.copy()

    def get_num_songs_new(self):
        return self.num_total_songs

    def get_num_songs_w_liked_songs(self):
        return self.num_total_songs_w_liked_songs

if __name__ == "__main__":
    pass
