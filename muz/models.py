# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
import json


class Playlists(models.Model):
    playlist_id = models.TextField(primary_key=True, blank=True)
    user_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'playlists'


class PlaylistsSongs(models.Model):
    playlist_id = models.TextField(blank=True, null=True)
    song_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'playlists_songs'


class Songs(models.Model):
    song_id = models.TextField(primary_key=True, blank=True)

    class Meta:
        managed = False
        db_table = 'songs'


class SongsPlaylists(models.Model):
    song_id = models.TextField(blank=True, null=True)
    playlist_id = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'songs_playlists'


class Users(models.Model):
    user_id = models.TextField(primary_key=True, blank=True)
    representation = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'


class CommunityModel(models.Model):
    client_id = models.CharField(max_length=255, primary_key=True)  # Use client_id as the primary key
    users = models.JSONField(default=list)
    current_score = models.FloatField(default=-1)
    last_best_score = models.FloatField(default=0)
    time_since_best_score = models.FloatField(default=0)
    slow_improvement_flag = models.IntegerField(default=0)
    current_labels = models.JSONField(default=list)
    suggestions = models.JSONField(default=list)
    suggestions_scores = models.JSONField(default=dict)
    users_scores = models.JSONField(default=dict)
    feedback_songs = models.JSONField(default=list)

    def __str__(self):
        return self.client_id


