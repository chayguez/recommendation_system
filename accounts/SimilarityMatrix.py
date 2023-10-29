from .Database import DataBase
import numpy as np
import time
from sklearn.cluster import SpectralClustering
from .Client import Client
import torch
#import cudf
#import cugraph


class SpectralException(Exception):
    def __init__(self, message):
        super().__init__(message)


class SimilarityMatrix:
    """
    - A matrix based on the playlist's songs of our user
    - For each playlist added, the similarity weight between each couple of songs is incremented by one
    """

    def __init__(self, client_id):
        self.original_label = []
        self.client = Client(client_id)
        self.database = DataBase()
        self.max_songs = self.client.get_num_songs_new()
        self.matrix_new = np.zeros((self.max_songs, self.max_songs))
        self.indexMatrix_to_songId_new = []
        self.init_matrix_indexes()
        self.init_original_labels()

    def init_matrix_indexes(self):
        songs_list_w_duplicates = []
        for playlist in self.client.get_playlists_id_new():
            songs_list = self.client.get_playlist_songs(playlist)
            songs_list_w_duplicates.extend(songs_list)
        self.indexMatrix_to_songId_new = list(set(songs_list_w_duplicates))
        self.indexMatrix_to_songId_new.sort()
        self.original_label = np.full(self.max_songs, -1)

    def init_original_labels(self):
        current_label = 0
        for playlist in self.client.get_playlists_id_new():
            songs_list = self.client.get_playlist_songs(playlist)
            indexes = np.where(np.isin(self.indexMatrix_to_songId_new, songs_list))[0]
            for index in indexes:
                self.original_label[index] = current_label

            current_label += 1

    def add_user(self, user_id):
        playlists_id = self.database.get_user_playlists(user_id)
        for playlist_id in playlists_id:
            self.add_per_playlist(playlist_id)

    def remove_user(self, user_id):
        playlists_id = self.database.get_user_playlists(user_id)
        for playlist_id in playlists_id:
            self.remove_per_playlist(playlist_id)

    def add_per_playlist(self, playlist_id):
        playlist_songs_brut = self.database.get_playlist_songs(playlist_id[0])
        playlist_songs = [x for (x,) in playlist_songs_brut]
        indexes = np.where(np.isin(self.indexMatrix_to_songId_new, playlist_songs))[0]
        for index1 in indexes:
            for index2 in indexes:
                if index2 != index1:
                    self.matrix_new[index1][index2] += 1

    def remove_per_playlist(self, playlist_id):
        playlist_songs_brut = self.database.get_playlist_songs(playlist_id[0])
        playlist_songs = [x for (x,) in playlist_songs_brut]
        indexes = np.where(np.isin(self.indexMatrix_to_songId_new, playlist_songs))[0]
        for index1 in indexes:
            for index2 in indexes:
                if index2 != index1:
                    self.matrix_new[index1][index2] -= 1

    def spectral_clustering(self):
        zero_index = np.where(~self.matrix_new.any(axis=0))[0]
        assert len(np.where(~self.matrix_new.any(axis=0))[0]) == len(np.where(~self.matrix_new.any(axis=1))[0])
        # remove all unnecessary songs from similarity matrix
        matrix_cropped = self.matrix_new[~np.all(self.matrix_new == 0, axis=0)]
        matrix_cropped = matrix_cropped[:, ~np.all(matrix_cropped == 0, axis=0)]
        intersection_w_duplicates = np.sum(matrix_cropped)
        # crop the original labels
        original_labels_cropped = [label for i, label in enumerate(self.original_label) if i not in zero_index]
        # Spectral Clustering
        num_playlist = len(set(original_labels_cropped))
        if len(matrix_cropped) != 0:
            current_labels = self.sc(num_playlist, matrix_cropped)
        else:
            current_labels = None
            print('no intersection with community')
        return original_labels_cropped, current_labels

    def get_num_songs_client(self):
        return self.client.get_num_songs_new()

    def sc(self, num_cluster, matrix):
        if torch.cuda.is_available():
            G = cugraph.Graph()

            # Convert the numpy matrix to cudf dataframe
            rows, cols = np.where(matrix != 0)
            weights = matrix[rows, cols]

            df = cudf.DataFrame({
                'src': rows.astype(np.int32),
                'dst': cols.astype(np.int32),
                'weights': weights
            })

            # Add edges to the graph
            G.from_cudf_edgelist(df, source='src', destination='dst', edge_attr='weights')

            # G.from_numpy_array(adj_matrix)
            print('num cluster :', num_cluster)
            spectral_clusters = cugraph.spectralBalancedCutClustering(G, num_cluster)  # , num_eigen_vects=3
            # and here I need the labels associated with each index of adj_matrix
            # Sort the dataframe by 'vertex'
            spectral_clusters = spectral_clusters.sort_values('vertex')

            labels = spectral_clusters['cluster']

            # Convert labels to a numpy array
            labels_array = labels.to_arrow().to_pandas().values
            print('computing sc using the gpu')
            return labels_array
        else:
            matrix = matrix + 0.01
            model = SpectralClustering(random_state=0, n_clusters=num_cluster, affinity='precomputed', ).fit(matrix)
            current_labels = model.labels_
            print('computing sc using the cpu')
            return current_labels


class SimilarityMatrix_Extended(SimilarityMatrix):
    def __init__(self, client_id, current_users):
        self.advisors = current_users
        super().__init__(client_id)
        self.songs_in_neighbours_not_in_user = list(set(self.database.get_songs_in_neighbours_not_in_user(self.client.id, self.advisors)))
        self.songs_in_neighbours_not_in_user.sort()
        self.max_songs = len(self.songs_in_neighbours_not_in_user) + self.client.get_num_songs_w_liked_songs()
        self.matrix_new = np.zeros((self.max_songs, self.max_songs))

    def init_original_labels(self):
        pass

    def init_matrix_indexes(self):
        songs_list_w_duplicates = []
        for user_id in [self.client.id] + self.advisors:
            playlists_id = self.database.get_user_playlists(user_id)
            for playlist_id in playlists_id:
                playlist_songs_brut = self.database.get_playlist_songs(playlist_id[0])
                playlist_songs = [x for (x,) in playlist_songs_brut]
                songs_list_w_duplicates.extend(playlist_songs)

        self.indexMatrix_to_songId_new = list(set(songs_list_w_duplicates))
        self.indexMatrix_to_songId_new.sort()
        self.original_label = np.full(self.max_songs, -1)

    def remove_by_song(self, song_id):
        indexes = np.where(np.isin(self.indexMatrix_to_songId_new, song_id))[0]
        self.remove_by_index(indexes)

    def remove_by_index(self, indexes):
        self.matrix_new = np.delete(np.delete(self.matrix_new, indexes, axis=1), indexes, axis=0)
        self.indexMatrix_to_songId_new = np.delete(self.indexMatrix_to_songId_new, indexes)
        self.songs_in_neighbours_not_in_user = [song for song in self.songs_in_neighbours_not_in_user if song in self.indexMatrix_to_songId_new]

    def spectral_clustering_fetching(self, num_cluster):
        if len(self.matrix_new) == 0:
            raise SpectralException("matrix size is 0")

        print('matrix size : ', len(self.matrix_new))
        print('potential songs to suggest :', len(self.songs_in_neighbours_not_in_user))
        current_labels = self.sc(num_cluster, self.matrix_new)

        return self.indexMatrix_to_songId_new, current_labels





