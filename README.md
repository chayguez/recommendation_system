# Recommendation System

## Modules

1. **Community Optimizer (user-based module/unsupervised learning)** : looks for the community of users which is the most similar to our user
2. **Suggested Songs Fetching (item-based module/unsupervised learning)** : provides songs similar to our user’s, out of a pool of songs retrieved from a community of users.
3. **Feedback-Driven Refiner (asynchronous module/supervised learning)** : updates the community based on client feedback from previous songs suggestion batches.

## Django App

### Sequence Diagram
![Sequence diagram MUZ APP](https://github.com/user-attachments/assets/0037ce8c-be89-429f-86ed-277ad00f703a)

---

### Web Interface
1. **Login View**
   - Secure authentication via Spotify credentials.
   - Support for multiple clients with pre-registered test accounts.
   - Persistent background processing for logged-out users.
2. **Suggestion View**
   - Displays daily book suggestions with options to 'Like' or 'Dislike.'
   - User feedback refines future suggestions in real time.

### Backend Components
1. **Task Management**:
   - Asynchronous task execution using Celery.
   - Tasks include community optimization and suggestion computation.
2. **Algorithms**:
   - Iterative spectral clustering for fine-grained grouping of similar items.
   - Community-driven similarity score evaluation.

---

## Prompt Overview

The application requires three terminals for operation:

1. **Server Management**:
   - Run `python manage.py makemigrations`, `python manage.py migrate`, and `python manage.py runserver`.

2. **Celery Broker Management**:
   - Start with the command: `celery -A spotify worker --loglevel=info`.

3. **Celery Beat Management**:
   - Start with the command: `celery -A spotify beat -l info`.

---

## Usage Flow

1. **Login**:
   - Users log in using Spotify credentials, initializing the recommendation process.
2. **Community Optimization**:
   - Continuous improvement of user communities for personalized suggestions.
3. **Suggestions**:
   - Recommendations are fetched daily, and user feedback influences future suggestions.

---

## Technologies Used

- **Backend**: Django, Celery
- **Clustering Algorithms**: Spectral Clustering
- **Task Scheduling**: Celery Beat
- **Database**: User and community data are dynamically managed.

---

## Testing Accounts

Two test accounts are available:
1. `muz_client`  
   - Email: `chayguez@gmail.com`
   - Password: `********`

2. `muz_client_2`  
   - Email: `chayguez@campus.technion.ac.il`
   - Password: `**********`

---
