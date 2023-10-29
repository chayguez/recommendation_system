import random
import numpy as np
from sklearn.metrics.cluster import adjusted_rand_score
import time
from .Database import DataBase
from .SimilarityMatrix import SimilarityMatrix,SimilarityMatrix_Extended,SpectralException
from muz.models import *


class Community:
    """
    For a particular client a Community represent the current set of users that our future suggestions comes from
    """
    def __init__(self, _client_id):
        self.client_id = _client_id
        self.database = DataBase()
        self.similarity_matrix = SimilarityMatrix(_client_id)  # refactor
        self.users = []
        self.current_score = 0
        self.last_best_score = time.time()
        self.time_since_best_score = 0
        self.slow_improvement_flag = 0
        self.current_labels = []
        self.suggestions = []
        self.suggestions_scores = {}
        self.users_scores = {}
        self.feedback_songs = []
        random.seed(10)

    def get_new_user(self):
        """
        :return: a random but new user to potentially add to our community
        """
        new_user_id_brut = self.database.get_random_user()
        new_user_id = new_user_id_brut[0]
        while new_user_id in [self.client_id] + self.users:
            new_user_id_brut = self.database.get_random_user()
            new_user_id = new_user_id_brut[0]
        return new_user_id

    def find_best_sub_community(self):
        """
        try each time a new combination of users and check if this one is better than the previous one
        """
        new_user_to_test = self.get_new_user()
        jaccard_client_community = self.database.jaccard_community(self.client_id, self.users)
        while self.slow_improvement_flag:
            new_user_to_test = self.get_new_user()
            jaccard_client_user = self.database.jaccard(self.client_id, new_user_to_test)
            if jaccard_client_user > jaccard_client_community:
                break

        print('new user to test :', new_user_to_test)
        self.users.append(new_user_to_test)
        self.similarity_matrix.add_user(new_user_to_test)
        score = self.compute_community_score()
        print('Community of users: ', self.users, 'would have a similarity score with current client of', score)
        if score > self.current_score:
            self.last_best_score = time.time()
            self.time_since_best_score = 0
            self.current_score = score
            user_to_remove = None
        else:
            user_to_remove = new_user_to_test

        for _user in self.users:
            if _user != new_user_to_test:
                self.similarity_matrix.remove_user(_user)
                copy = self.users.copy()
                copy.remove(_user)
                score = self.compute_community_score()
                print('Community of users: ', copy, 'would have a similarity score with current client of', score)
                if score > self.current_score:
                    self.current_score = score
                    self.last_best_score = time.time()
                    self.time_since_best_score = 0
                    user_to_remove = _user
                self.similarity_matrix.add_user(_user)

        if user_to_remove is not None:
            self.similarity_matrix.remove_user(user_to_remove)
            self.users.remove(user_to_remove)

        for _user in self.users:
            if _user not in self.users_scores:
                self.users_scores[_user] = 0
        print('Current Best Score:', self.current_score)
        self.time_since_best_score = time.time() - self.last_best_score
        print('time since best score is:', self.time_since_best_score)

        # we check if we didn't get improvement for more than 5 min
        if self.time_since_best_score > 300:
            self.slow_improvement_flag = 1
        else:
            self.slow_improvement_flag = 0

    def compute_community_score(self):
        """
        how close this community is to our client?
        """
        original_labels, current_labels = self.similarity_matrix.spectral_clustering()

        # ari coeff
        if current_labels is None:
            ari = 0
        else:
            ari = (adjusted_rand_score(original_labels, current_labels)+1)/2
        print("ARI=", ari)

        # jaccard coeff
        jaccard = self.database.jaccard_community(self.client_id, self.users)
        print("Jaccard=", jaccard)

        # similarity score between the set of self.users and the client
        community_score = ari * jaccard

        return community_score

    def update_suggestions_list(self):
        """
        after assembling a team of relatively good users, it's time to fetch suggestions from those users
        """
        #self.suggestions = []  #############REMOVE
        #self.suggestions_scores = {}
        counter = 0

        num_cluster = 2
        similarity_matrix_for_suggestions = SimilarityMatrix_Extended(self.client_id, self.users)
        try:
            for user in self.users:
                similarity_matrix_for_suggestions.add_user(user)
            #while not self.suggestions_ready():
            while True:
                counter += 1
                print('current suggestions : ', self.suggestions)
                print('iterative spectral clustering iteration number:', counter)
                num_cluster = self.find_suggestions(similarity_matrix_for_suggestions, num_cluster)
        except SpectralException as SP_e:
            print('fetching algorithm has finished')

    def find_suggestions(self, similarity_matrix, num_cluster):
        """
        :param similarity_matrix: a SimilarityMatrix_Extended Object
        composed of songs from the current client and the community's user
        :param num_cluster: into how many clusters should spectral clustering cluster the similarity matrix
        :return: the number of clusters for the next iteration of spectral clustering
        """
        print(num_cluster, "clusters for client :", self.get_client_id())
        indexes_to_remove = []
        songs, labels = similarity_matrix.spectral_clustering_fetching(num_cluster)
        for i in range(num_cluster):
            indexes_label = np.where(np.isin(labels, i))[0]
            songs_cluster = [songs[j] for j in indexes_label]
            new_songs_for_user = [songs for songs in songs_cluster if songs in similarity_matrix.songs_in_neighbours_not_in_user]
            ratio = len(new_songs_for_user) / len(songs_cluster)
            print('ratio for cluster ', i, ' : ', ratio)
            if ratio < 0.2:
                self.update_suggestion_score(new_songs_for_user)
                new_suggestions = [song for song in new_songs_for_user if song not in self.suggestions]
                if len(new_suggestions) < len(self.users):
                    self.suggestions.extend(new_suggestions)
            if ratio == 0 or ratio == 1:
                indexes_to_remove.extend(indexes_label)
        similarity_matrix.remove_by_index(indexes_to_remove)
        if len(indexes_to_remove) == 0:
            if num_cluster+1 > len(similarity_matrix.indexMatrix_to_songId_new):
                return len(similarity_matrix.indexMatrix_to_songId_new)
            else:
                return num_cluster+1
        else:
            if num_cluster > len(similarity_matrix.indexMatrix_to_songId_new):
                return len(similarity_matrix.indexMatrix_to_songId_new)
            else:
                return num_cluster

    def suggestions_ready(self):
        """
        :return: indicates if we got enough suggestions
        """

        if len(self.suggestions) > 0:
            return True ######### REMOVE

        self.suggestions = [suggestion for suggestion in self.suggestions if suggestion not in self.feedback_songs]
        N = len(self.users)
        if len(self.suggestions) >= N:
            return True
        if len(self.suggestions_scores) > N:
            top_suggestions = sorted(self.suggestions_scores, key=self.suggestions_scores.get, reverse=True)[:N+1]
            top_suggestions_score = sorted(self.suggestions_scores.values(), reverse=True)[:N+1]
            if top_suggestions_score[N-1] == top_suggestions_score[N]:
                return False
            else:
                self.suggestions = top_suggestions[:N]
                return True
        else:
            return False

    def update_suggestion_score(self, suggestions):
        for song in suggestions:
            if song in self.suggestions_scores:
                self.suggestions_scores[song] += 1
            else:
                self.suggestions_scores[song] = 1

    def feedback_refiner(self, _song_id, liked):
        """
        :param _song_id: get the song that has been liked or disliked
        :param liked: true if the song has been liked, false otherwise
        Updates user's score in the community and remove it if necessary
        Make sure the disliked song won't appear in future suggestion and add the liked song to the client's liked_songs playlist
        """
        print('3. FEEDBACK REFINER')
        # remove the song from potential suggestions
        self.suggestions.remove(_song_id)
        # Get the users linked to the song we got feedback for
        users = self.database.get_users_with_song(_song_id)
        for user_id in users:
            if user_id in self.users_scores:
                # if the song was liked, improve user's score by one
                if liked:
                    self.users_scores[user_id] += 1
                    # add it the liked songs
                    self.database.add_song_to_liked_songs(_song_id, user_id)
                # if the song was disliked, reduce user's score by one and remove it if new score < -1
                else:
                    self.users_scores[user_id] -= 1
                    if self.users_scores[user_id] < -1 and user_id in self.users:
                        self.users.remove(user_id)
                        self.similarity_matrix.remove_user(user_id)

    def get_client_id(self):
        return self.client_id

    def get_suggestions(self):
        """
        :return the most recent suggestions
        """
        max_suggestions_amount = len(self.users)
        if len(self.suggestions) < max_suggestions_amount:
            return self.suggestions.copy()

        else:
            most_recent_suggestions = self.suggestions[-max_suggestions_amount:]
            return most_recent_suggestions


    def save_community_to_database(self):
        community_model = CommunityModel(
            client_id=self.client_id,
            users=self.users,
            current_score=self.current_score,
            last_best_score=self.last_best_score,
            time_since_best_score=self.time_since_best_score,
            slow_improvement_flag=self.slow_improvement_flag,
            current_labels=self.current_labels,
            suggestions=self.suggestions,
            suggestions_scores=self.suggestions_scores,
            users_scores=self.users_scores,
            feedback_songs=self.feedback_songs
        )
        community_model.save()

    def load_community_from_database(self):
        try:
            community_model = CommunityModel.objects.get(client_id=self.client_id)
        except CommunityModel.DoesNotExist:
            return
        self.users = community_model.users
        self.current_score = community_model.current_score
        self.last_best_score = community_model.last_best_score
        self.time_since_best_score = community_model.time_since_best_score
        self.slow_improvement_flag = community_model.slow_improvement_flag
        self.current_labels = community_model.current_labels
        self.suggestions = community_model.suggestions
        self.suggestions_scores = community_model.suggestions_scores
        self.users_scores = community_model.users_scores
        self.feedback_songs = community_model.feedback_songs
        for _user in self.users:
            self.similarity_matrix.add_user(_user)
        return


def community_optimizer(client_id):
    """
    :param client_id:
    Optimize the community by trying to integrate a new user from the database into the Community of client_id
    """
    community_instance = Community(client_id)
    community_instance.load_community_from_database()
    print("1. COMMUNITY OPTIMIZER")
    print("Current best community is :", community_instance.users)
    current_best_score = community_instance.current_score
    current_improvement_flag_state = community_instance.slow_improvement_flag
    print('Score to improve is :', current_best_score)

    print('Try to add another user in community of client :', community_instance.get_client_id())
    # here start the community optimizer algorithm.
    community_instance.find_best_sub_community()
    new_best_score = community_instance.current_score

    # if the integration of this new user resulted in a better similarity score we save the community in django database
    improvement_flag_new_state = community_instance.slow_improvement_flag
    if new_best_score > current_best_score or improvement_flag_new_state > current_improvement_flag_state:
        community_instance.save_community_to_database()
    return


def suggestion_songs_fetching(client_id):
    """
    :param client_id:
    :return: a list of suggested songs based on the Community of client_id stored in the django database
    """
    community_instance = Community(client_id)
    community_instance.load_community_from_database()
    print("2. SUGGESTED SONGS FETCHING", community_instance.get_client_id())
    print("Fetching songs from community of users:", community_instance.users)
    start = time.time()

    # here start the suggested songs fetching algorithm
    community_instance.update_suggestions_list()
    community_instance.save_community_to_database()

    suggestions = community_instance.get_suggestions()
    print('suggestions list for client : ', community_instance.get_client_id(), ' is ', suggestions)

    end = time.time()
    temps_execution = end - start
    h = int(temps_execution // 3600)
    m = int((temps_execution % 3600) // 60)
    s = int(temps_execution % 60)
    print("suggestions ready after {}h:{}min{}:sec".format(h, m, s))

    return suggestions
