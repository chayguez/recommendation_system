import sqlite3


class DataBase:

    def __init__(self):
        self.conn = sqlite3.connect('accounts/muz.db')
        self.database = self.conn.cursor()
        self.create_if_not_exists()
        self.genres = ['pop', 'rock', 'dance', 'electro', 'house', 'hip-hop', 'rap', 'variete francaise', 'r&b','soul']

    def create_if_not_exists(self):
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS playlists(
                playlist_id text PRIMARY KEY,
                user_id text)
        """)
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id text PRIMARY KEY,
                representation text)
        """)
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS songs(
                song_id text PRIMARY KEY) 
        """)
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS songs_playlists(
                song_id text,
                playlist_id text)
        """)

    def print_all(self):
        self.print_users_id()
        self.print_playlists()
        self.print_songs_playlists()

    def print_details(self):
        self.database.execute("SELECT COUNT(*) FROM playlists")
        print("number of playlist:")
        print(self.database.fetchone())
        self.database.execute("SELECT COUNT(*) FROM users")
        print("number of users:")
        print(self.database.fetchone())
        self.database.execute("SELECT COUNT(*) FROM songs")
        print("number of songs:")
        print(self.database.fetchone())
        self.database.execute("SELECT COUNT(*) FROM songs_playlists")
        print("number of songs from songs_playlist:")
        print(self.database.fetchone())

    def print_users_id(self):
        self.database.execute("SELECT user_id FROM users")
        print("all the users:")
        print(self.database.fetchall())

    def print_playlists(self):
        self.database.execute("SELECT playlist_id FROM playlists")
        print("all the playlists:")
        print(self.database.fetchall())

    def print_songs(self):
        self.database.execute("SELECT song_id FROM songs")
        print(self.database.fetchall())

    def print_songs_playlists(self):
        self.database.execute("SELECT * FROM songs_playlists")
        print("all the songs and their playlists:")
        print(self.database.fetchall())

    def end_connection(self):
        self.conn.commit()
        self.conn.close()

    def delete_all(self):
        self.database.execute('''DROP table playlists''')
        self.database.execute('''DROP table users''')
        self.database.execute('''DROP table songs''')
        self.database.execute('''DROP table songs_playlists''')

    def add_songs_table(self, tracks): #list of tracks
        if len(tracks) == 1:
            self.database.execute("INSERT INTO songs VALUES (?)", (tracks[0],))
        else:
            self.database.execute("SELECT * FROM songs WHERE song_id IN {}".format(tuple(tracks)))
            already_present_songs = self.database.fetchall()
            new_tracks_only = [(x,) for x in tracks if (x,) not in already_present_songs]
            self.database.executemany("INSERT INTO songs VALUES (?)", new_tracks_only)

    def add_user_table(self, user_id, user_grid):
        self.database.execute("INSERT INTO users VALUES (?,?)", (user_id, user_grid))

    def add_playlist_table2(self, playlist_id, owner_id): #not using it
        self.database.execute("SELECT * FROM playlists WHERE playlist_id = (?)", (playlist_id,))
        if self.database.fetchone() is None:
            self.database.execute("INSERT INTO playlists VALUES (?,?)", (playlist_id, owner_id))

    def add_playlist_table(self, playlists, user_id): #list of playlists
        if len(playlists)==1:
            self.database.execute("INSERT INTO playlists VALUES (?,?)", (playlists[0], user_id))
        else:
            self.database.execute("SELECT playlist_id FROM playlists WHERE playlist_id IN {}".format(tuple(playlists))) #BUG if number playlist =1
            already_present_playlists = self.database.fetchall()
            new_playlists_only_user = [(x, user_id) for x in playlists if (x,) not in already_present_playlists]
            self.database.executemany("INSERT INTO playlists VALUES (?,?)", new_playlists_only_user)

    def add_songs_to_playlists_table(self, songs_playlists_id): #list of tuple [(song, playlist)]
        if len(songs_playlists_id)==1:
            self.database.execute("INSERT INTO playlists VALUES (?,?)", songs_playlists_id[0])
        else:
            playlists = list([x[1] for x in songs_playlists_id]) #ATTENTION! si il n'y a qu'une playlist avec une chanson-> bug a tuple(playlists)
            self.database.execute("SELECT * FROM songs_playlists WHERE playlist_id IN {}".format(tuple(playlists)))
            already_present_playlists = self.database.fetchall()
            new_playlists_only = [x for x in songs_playlists_id if x not in already_present_playlists]
            self.database.executemany("INSERT INTO songs_playlists VALUES (?,?)", new_playlists_only)

    def get_user_playlists(self, user_id):
        self.database.execute("SELECT playlist_id FROM playlists WHERE user_id = (?)",(user_id,))
        return self.database.fetchall()

    def get_all_users(self):
        self.database.execute("SELECT * FROM users")
        return self.database.fetchall()

    def get_playlist_songs(self, playlist_id):
        self.database.execute("""
        SELECT s.song_id
        FROM songs_playlists sp 
        INNER JOIN songs s ON s.song_id = sp.song_id
        WHERE sp.playlist_id = (?)
        """, (playlist_id,))
        return self.database.fetchall()

    def get_num_songs(self, users_id):
        """
        :param users_id: list of users
        :return: total number of songs for those users
        """
        self.database.execute("""
                SELECT COUNT(distinct songs.song_id)
                FROM songs_playlists
                INNER JOIN songs ON songs.song_id = songs_playlists.song_id
                WHERE songs_playlists.playlist_id in 
                (SELECT playlist_id FROM playlists WHERE playlists.user_id in {})""".format(tuple(users_id)))
        return self.database.fetchone()

    def get_dup_songs(self, playlist_id, users_id):
        self.database.execute("""
                SELECT song_id
                FROM songs_playlists
                WHERE songs_playlists.song_id in 
                (SELECT song_id FROM songs_playlists WHERE songs_playlists.playlist_id = (?))
                AND songs_playlists.playlist_id in 
                (SELECT playlist_id FROM playlists WHERE playlists.user_id in {})
                GROUP BY song_id
                HAVING COUNT(*)>1
                """.format(tuple(users_id)), (playlist_id,))
        return self.database.fetchall()

    def get_songs_in_neighbours_not_in_user(self, user_id, neighbours_id):
        """
        :param user_id:
        :param neighbours_id:
        :return: all the songs that are in neighbours but are not in user_id
        """

        if len(neighbours_id) == 0:
            mylist = []
            return mylist
        neighbours_tuple = tuple(neighbours_id) if len(neighbours_id) > 1 else (neighbours_id[0],)
        if len(neighbours_id) > 1:
            self.database.execute("""
                    SELECT song_id
                    FROM songs_playlists
                    WHERE songs_playlists.playlist_id in 
                    (SELECT playlist_id FROM playlists WHERE playlists.user_id in {})
                    EXCEPT
                    SELECT song_id
                    FROM songs_playlists
                    WHERE songs_playlists.playlist_id in 
                    (SELECT playlist_id FROM playlists WHERE playlists.user_id = (?))
                    """.format(neighbours_tuple), (user_id,))
            mylist = [x for (x,) in self.database.fetchall()]
            return mylist
        else:
            neighbours_str = ','.join("'" + neighbour_id + "'" for neighbour_id in neighbours_id)

            self.database.execute("""
                SELECT song_id
                FROM songs_playlists
                WHERE songs_playlists.playlist_id IN (
                    SELECT playlist_id
                    FROM playlists
                    WHERE playlists.user_id IN ({})
                )
                EXCEPT
                SELECT song_id
                FROM songs_playlists
                WHERE songs_playlists.playlist_id IN (
                    SELECT playlist_id
                    FROM playlists
                    WHERE playlists.user_id = (?)
                )
            """.format(neighbours_str), (user_id,))
            mylist = [x for (x,) in self.database.fetchall()]
            return mylist

    def jaccard_community(self, user_id, user_id_list):
        # Fetch the songs associated with the single user (user_id)
        self.database.execute("""
            SELECT song_id FROM songs_playlists
            WHERE playlist_id IN (
                SELECT playlist_id FROM playlists
                WHERE user_id = ?
            )
        """, (user_id,))

        songs_single_user = set(song[0] for song in self.database.fetchall())

        # Fetch the songs associated with the union of users (user_id_list)
        all_songs_union = set()
        intersection_size = 0
        for user in user_id_list:
            self.database.execute("""
                SELECT song_id FROM songs_playlists
                WHERE playlist_id IN (
                    SELECT playlist_id FROM playlists
                    WHERE user_id = ?
                )
            """, (user,))
            songs_union = set(song[0] for song in self.database.fetchall())
            intersection_size_user = len(songs_single_user.intersection(songs_union))
            intersection_size += intersection_size_user
            all_songs_union.update(songs_union)

        # Calculate the intersection of the single user's songs and the union of all users' songs
        union = songs_single_user.union(all_songs_union)
        jaccard = intersection_size / len(songs_single_user)
        return jaccard

    def jaccard(self, user_id1, user_id2):
        # Fetch the songs associated with user_id1
        self.database.execute("""
            SELECT song_id FROM songs_playlists
            WHERE playlist_id IN (
                SELECT playlist_id FROM playlists
                WHERE user_id = ?
            )
        """, (user_id1,))
        songs1 = set(song[0] for song in self.database.fetchall())

        # Fetch the songs associated with user_id2
        self.database.execute("""
            SELECT song_id FROM songs_playlists
            WHERE playlist_id IN (
                SELECT playlist_id FROM playlists
                WHERE user_id = ?
            )
        """, (user_id2,))
        songs2 = set(song[0] for song in self.database.fetchall())

        # Calculate the intersection size
        intersection_size = len(songs1.intersection(songs2))
        union_size = len(songs1.union(songs2))
        jaccard = intersection_size/union_size
        return jaccard

    def delete_unique_songs(self):
        self.database.execute("""
                SELECT song_id
                FROM songs_playlists
                GROUP BY song_id
                HAVING COUNT(*)=1
                """)
        unique_songs = [x for (x,) in self.database.fetchall()]
        self.database.execute("""
                DELETE FROM songs_playlists
                WHERE songs_playlists.song_id in {}
                """.format(tuple(unique_songs)))

        self.database.execute("""
                DELETE FROM songs
                Where songs.song_id in {}
                """.format(tuple(unique_songs)))
        return len(unique_songs)

    def get_dup_songs_in_user(self, user_id):
        """
        :param user_id:
        :return: (songs_id, playlist_id) for every songs that has a duplicate in an other playlist
        from the same user_id
        """
        self.database.execute("""
                        SELECT a.song_id, a.playlist_id
                        FROM (SELECT * FROM songs_playlists 
                        WHERE playlist_id in 
                        (SELECT playlist_id FROM playlists WHERE playlists.user_id = (?))) a
                        JOIN ( SELECT * FROM songs_playlists
                        WHERE playlist_id in 
                        (SELECT playlist_id FROM playlists WHERE playlists.user_id = (?))
                        GROUP BY song_id
                        HAVING COUNT(song_id)>1) b
                        ON a.song_id = b.song_id
                        """, (user_id, user_id))
        return self.database.fetchall()

    def test(self, user_id):
        self.database.execute("""
                                SELECT *
                                FROM playlists a
                                JOIN ( SELECT * FROM songs_playlists 
                                WHERE playlist_id in 
                                (SELECT playlist_id FROM playlists WHERE playlists.user_id = (?))
                                GROUP BY song_id
                                HAVING COUNT(song_id)>1) b
                                ON a.playlist_id = b.playlist_id
                                """, (user_id,))
        return self.database.fetchall()

    def get_random_user(self):
        self.database.execute("SELECT user_id FROM users ORDER BY RANDOM() LIMIT 1")
        tup = self.database.fetchone()
        return tup

    def find_row_by_userid(self, user_id):
        self.database.execute("SELECT rowid FROM users WHERE user_id = (?)", (user_id,))
        return self.database.fetchone()

    def return_data_from_users(self):
        self.database.execute("SELECT * FROM users")
        return self.database.fetchall()

    def number_of_rows_users(self):
        self.database.execute("SELECT COUNT(*) FROM users")
        return self.database.fetchone()

    def find_userid_by_row(self, row): #BE CAREFUL THERE IS A +1! Useful for BallTree Please do not remove it
        self.database.execute("SELECT user_id FROM users WHERE rowid = (?)", (row+1,))
        return self.database.fetchone()

    def get_users_with_song(self, song_id):
        self.database.execute("""
            SELECT DISTINCT playlists.user_id
            FROM playlists 
            JOIN songs_playlists ON playlists.playlist_id = songs_playlists.playlist_id
            WHERE songs_playlists.song_id = ?
        """, (song_id,))
        user_ids = [row[0] for row in self.database.fetchall()]
        return user_ids

    def add_song_to_liked_songs(self, song_id, user_id):
        playlist_id = 'liked_songs_' + user_id
        self.database.execute("INSERT INTO songs_playlists (song_id, playlist_id) VALUES (?, ?)",
                              (song_id, playlist_id))
        self.database.execute("INSERT INTO songs (song_id) VALUES (?)", (song_id,))
        self.conn.commit()



if __name__ == "__main__":
    database = DataBase()
    print(database.test('12167242574'))