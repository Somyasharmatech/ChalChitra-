import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple
import json

# Get database connection from environment variables
import streamlit as st
DATABASE_URL = st.secrets["DATABASE_URL"]["url"]

# Create SQLAlchemy engine with SSL disabled for development
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={
        "sslmode": "require",
        "keepalives": 1,
        "keepalives_idle": 30
    }
)


def get_connection():
    """Get a database connection"""
    return engine.connect()

def execute_query(query, params=None):
    """Execute a SQL query with parameters"""
    try:
        with get_connection() as conn:
            result = conn.execute(text(query), params or {})
            conn.commit()
            return result
    except SQLAlchemyError as e:
        st.error(f"Database error: {str(e)}")
        return None

def fetch_all(query, params=None):
    """Execute a query and fetch all results"""
    result = execute_query(query, params)
    if result is not None:
        return result.fetchall()
    return []

def fetch_one(query, params=None):
    """Execute a query and fetch one result"""
    result = execute_query(query, params)
    if result is not None:
        return result.fetchone()
    return None

def query_to_dataframe(query, params=None):
    """Execute a query and return results as a pandas DataFrame"""
    try:
        with get_connection() as conn:
            return pd.read_sql(text(query), conn, params=params)
    except SQLAlchemyError as e:
        st.error(f"Database error: {str(e)}")
        return pd.DataFrame()

# User-related functions
def get_or_create_user(session_id):
    """Get a user by session_id or create if not exists"""
    user = fetch_one(
        "SELECT id FROM users WHERE session_id = :session_id",
        {"session_id": session_id}
    )
    
    if not user:
        result = execute_query(
            "INSERT INTO users (session_id) VALUES (:session_id) RETURNING id",
            {"session_id": session_id}
        )
        if result:
            user = result.fetchone()
    
    return user[0] if user else None

def create_user_tables():
    """Create user authentication tables if they don't exist"""
    # Create users table
    execute_query("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            session_id VARCHAR(255) UNIQUE,
            username VARCHAR(100) UNIQUE,
            password_hash VARCHAR(255),
            email VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    def create_preference_tables():
    """Create user preference tables if they don't exist"""
    # Create user_preferences table
    execute_query("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) UNIQUE,
            min_year INTEGER,
            max_year INTEGER,
            min_rating FLOAT,
            preferred_languages TEXT[],
            runtime_range INTEGER[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create user_genre_preferences table
    execute_query("""
        CREATE TABLE IF NOT EXISTS user_genre_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            genre_id INTEGER REFERENCES genres(id),
            UNIQUE (user_id, genre_id)
    """)
    
    # Create user_auth table
    execute_query("""
        CREATE TABLE IF NOT EXISTS user_auth (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            auth_token VARCHAR(255) UNIQUE,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

def create_user_account(username, password, email=None):
    """Create a new user account with password"""
    import hashlib
    
    # Hash the password (in a real app, use a proper password hashing library)
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # First check if username already exists
    existing_user = fetch_one(
        "SELECT id FROM users WHERE username = :username",
        {"username": username}
    )
    
    if existing_user:
        return None, "Username already exists"
    
    # Create new user
    result = execute_query(
        """
        INSERT INTO users (username, password_hash, email)
        VALUES (:username, :password_hash, :email)
        RETURNING id
        """,
        {
            "username": username,
            "password_hash": password_hash,
            "email": email
        }
    )
    
    if result:
        user_id = result.fetchone()[0]
        return user_id, None
    
    return None, "Error creating account"

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    import hashlib
    
    # Hash the provided password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # Check if user exists with matching password
    user = fetch_one(
        """
        SELECT id
        FROM users
        WHERE username = :username AND password_hash = :password_hash
        """,
        {
            "username": username,
            "password_hash": password_hash
        }
    )
    
    if user:
        # Generate auth token
        import uuid
        import datetime
        
        auth_token = str(uuid.uuid4())
        expires_at = datetime.datetime.now() + datetime.timedelta(days=7)
        
        # Store token in database
        execute_query(
            """
            INSERT INTO user_auth (user_id, auth_token, expires_at)
            VALUES (:user_id, :auth_token, :expires_at)
            """,
            {
                "user_id": user[0],
                "auth_token": auth_token,
                "expires_at": expires_at
            }
        )
        
        return user[0], auth_token
    
    return None, None

def validate_token(auth_token):
    """Validate a user auth token"""
    import datetime
    
    user = fetch_one(
        """
        SELECT u.id, u.username
        FROM user_auth ua
        JOIN users u ON ua.user_id = u.id
        WHERE ua.auth_token = :auth_token AND ua.expires_at > :now
        """,
        {
            "auth_token": auth_token,
            "now": datetime.datetime.now()
        }
    )
    
    if user:
        return user[0], user[1]
    
    return None, None

def get_username_by_id(user_id):
    """Get username by user ID"""
    user = fetch_one(
        "SELECT username FROM users WHERE id = :user_id",
        {"user_id": user_id}
    )
    
    return user[0] if user else None

def save_user_preferences(user_id, preferences):
    """Save or update user preferences"""
    # Extract preference values
    min_year = preferences.get('year_range', [1990, 2023])[0]
    max_year = preferences.get('year_range', [1990, 2023])[1]
    min_rating = preferences.get('min_rating', 7.0)
    languages = preferences.get('languages', ['en'])
    runtime_range = preferences.get('runtime_range')
    
    # Convert Python list to PostgreSQL array
    languages_array = "{" + ",".join(languages) + "}"
    
    # Convert runtime_range to PostgreSQL array if it exists
    runtime_array = "NULL"
    if runtime_range:
        runtime_array = "{" + ",".join(map(str, runtime_range)) + "}"
    
    # Check if user preferences already exist
    user_pref = fetch_one(
        "SELECT id FROM user_preferences WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    if user_pref:
        # Update existing preferences
        execute_query(
            """
            UPDATE user_preferences 
            SET min_year = :min_year, max_year = :max_year, 
                min_rating = :min_rating, preferred_languages = :languages,
                runtime_range = :runtime_range, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = :user_id
            """,
            {
                "user_id": user_id,
                "min_year": min_year,
                "max_year": max_year,
                "min_rating": min_rating,
                "languages": languages_array,
                "runtime_range": runtime_array
            }
        )
    else:
        # Insert new preferences
        execute_query(
            """
            INSERT INTO user_preferences 
            (user_id, min_year, max_year, min_rating, preferred_languages, runtime_range)
            VALUES (:user_id, :min_year, :max_year, :min_rating, :languages, :runtime_range)
            """,
            {
                "user_id": user_id,
                "min_year": min_year,
                "max_year": max_year,
                "min_rating": min_rating,
                "languages": languages_array,
                "runtime_range": runtime_array
            }
        )
    
    # Clear existing genre preferences
    execute_query(
        "DELETE FROM user_genre_preferences WHERE user_id = :user_id",
        {"user_id": user_id}
    )
    
    # Save genre preferences
    genres = preferences.get('genres', [])
    for genre_id in genres:
        execute_query(
            """
            INSERT INTO user_genre_preferences (user_id, genre_id)
            VALUES (:user_id, (SELECT id FROM genres WHERE tmdb_id = :genre_id))
            ON CONFLICT (user_id, genre_id) DO NOTHING
            """,
            {"user_id": user_id, "genre_id": genre_id}
        )

def get_user_preferences(user_id):
    """Get user preferences from database"""
    preferences = fetch_one(
        """
        SELECT min_year, max_year, min_rating, preferred_languages, runtime_range
        FROM user_preferences
        WHERE user_id = :user_id
        """,
        {"user_id": user_id}
    )
    
    genre_ids = [row[0] for row in fetch_all(
        """
        SELECT g.tmdb_id
        FROM user_genre_preferences ugp
        JOIN genres g ON ugp.genre_id = g.id
        WHERE ugp.user_id = :user_id
        """,
        {"user_id": user_id}
    )]
    
    if preferences:
        return {
            'year_range': [preferences[0], preferences[1]],
            'min_rating': preferences[2],
            'languages': list(preferences[3]),
            'runtime_range': list(preferences[4]) if preferences[4] else None,
            'genres': genre_ids
        }
    
    return {}

# Movie-related functions
def save_movie(movie_data):
    """Save a movie to the database if it doesn't exist"""
    movie = fetch_one(
        "SELECT id FROM movies WHERE tmdb_id = :tmdb_id", 
        {"tmdb_id": movie_data['id']}
    )
    
    if not movie:
        # Extract movie data
        release_date = movie_data.get('release_date')
        
        result = execute_query(
            """
            INSERT INTO movies 
            (tmdb_id, title, release_date, poster_path, vote_average, overview, original_language, backdrop_path, runtime)
            VALUES (:tmdb_id, :title, :release_date, :poster_path, :vote_average, :overview, :original_language, :backdrop_path, :runtime)
            RETURNING id
            """,
            {
                "tmdb_id": movie_data['id'],
                "title": movie_data['title'],
                "release_date": release_date,
                "poster_path": movie_data.get('poster_path'),
                "vote_average": movie_data.get('vote_average'),
                "overview": movie_data.get('overview'),
                "original_language": movie_data.get('original_language'),
                "backdrop_path": movie_data.get('backdrop_path'),
                "runtime": movie_data.get('runtime')
            }
        )
        
        if result:
            movie_id = result.fetchone()[0]
            
            # Save genres
            genres = []
            if 'genres' in movie_data:
                genres = [(g, None) for g in movie_data['genres']]
            elif 'genre_ids' in movie_data:
                genres = [(None, g) for g in movie_data['genre_ids']]
            
            for genre_name, genre_id in genres:
                if genre_name:
                    # Save genre by name
                    result = execute_query(
                        """
                        INSERT INTO genres (name) 
                        VALUES (:name)
                        ON CONFLICT (name) DO UPDATE SET name = :name
                        RETURNING id
                        """,
                        {"name": genre_name}
                    )
                    
                    if result:
                        genre_db_id = result.fetchone()[0]
                        execute_query(
                            """
                            INSERT INTO movie_genres (movie_id, genre_id)
                            VALUES (:movie_id, :genre_id)
                            ON CONFLICT (movie_id, genre_id) DO NOTHING
                            """,
                            {"movie_id": movie_id, "genre_id": genre_db_id}
                        )
                elif genre_id:
                    # Save genre by TMDB ID
                    execute_query(
                        """
                        INSERT INTO movie_genres (movie_id, genre_id)
                        SELECT :movie_id, id FROM genres WHERE tmdb_id = :genre_id
                        ON CONFLICT (movie_id, genre_id) DO NOTHING
                        """,
                        {"movie_id": movie_id, "genre_id": genre_id}
                    )
            
            return movie_id
    else:
        return movie[0]

def save_genre_mapping(genre_id, genre_name):
    """Save genre mapping from TMDB ID to name"""
    execute_query(
        """
        INSERT INTO genres (tmdb_id, name)
        VALUES (:tmdb_id, :name)
        ON CONFLICT (tmdb_id) DO UPDATE SET name = :name
        """,
        {"tmdb_id": genre_id, "name": genre_name}
    )

def save_user_rating(user_id, movie_data, rating):
    """Save a user's rating for a movie"""
    # First save the movie if it doesn't exist
    movie_id = save_movie(movie_data)
    
    if movie_id:
        execute_query(
            """
            INSERT INTO user_ratings (user_id, movie_id, rating)
            VALUES (:user_id, :movie_id, :rating)
            ON CONFLICT (user_id, movie_id) DO UPDATE SET rating = :rating
            """,
            {"user_id": user_id, "movie_id": movie_id, "rating": rating}
        )
        return True
    return False

def save_watched_movie(user_id, movie_data):
    """Mark a movie as watched by the user"""
    # First save the movie if it doesn't exist
    movie_id = save_movie(movie_data)
    
    if movie_id:
        execute_query(
            """
            INSERT INTO user_watched_movies (user_id, movie_id)
            VALUES (:user_id, :movie_id)
            ON CONFLICT (user_id, movie_id) DO NOTHING
            """,
            {"user_id": user_id, "movie_id": movie_id}
        )
        return True
    return False

def get_user_movie_ratings(user_id, limit=10):
    """Get a user's movie ratings"""
    return fetch_all(
        """
        SELECT m.tmdb_id, m.title, m.poster_path, m.release_date, m.vote_average, r.rating
        FROM user_ratings r
        JOIN movies m ON r.movie_id = m.id
        WHERE r.user_id = :user_id
        ORDER BY r.created_at DESC
        LIMIT :limit
        """,
        {"user_id": user_id, "limit": limit}
    )

def get_user_watched_movies(user_id, limit=20):
    """Get movies watched by a user"""
    return fetch_all(
        """
        SELECT m.tmdb_id, m.title, m.poster_path, m.release_date, m.vote_average
        FROM user_watched_movies w
        JOIN movies m ON w.movie_id = m.id
        WHERE w.user_id = :user_id
        ORDER BY w.watched_at DESC
        LIMIT :limit
        """,
        {"user_id": user_id, "limit": limit}
    )

def get_popular_movies_from_db(limit=10):
    """Get popular movies from the database based on user ratings"""
    return fetch_all(
        """
        SELECT m.tmdb_id, m.title, m.poster_path, m.release_date, m.vote_average, 
               COUNT(r.id) as rating_count, AVG(r.rating) as avg_rating
        FROM movies m
        JOIN user_ratings r ON m.id = r.movie_id
        GROUP BY m.id
        HAVING COUNT(r.id) >= 3
        ORDER BY avg_rating DESC
        LIMIT :limit
        """,
        {"limit": limit}
    )

def get_similar_movies_from_db(movie_id, limit=6):
    """Find similar movies based on genre overlap"""
    return fetch_all(
        """
        SELECT m.tmdb_id, m.title, m.poster_path, m.release_date, m.vote_average,
               COUNT(mg2.genre_id) as genre_overlap
        FROM movies m
        JOIN movie_genres mg ON m.id = mg.movie_id
        JOIN movie_genres mg2 ON mg.genre_id = mg2.genre_id
        JOIN movies m2 ON mg2.movie_id = m2.id
        WHERE m2.tmdb_id = :movie_id AND m.tmdb_id != :movie_id
        GROUP BY m.id
        ORDER BY genre_overlap DESC, m.vote_average DESC
        LIMIT :limit
        """,
        {"movie_id": movie_id, "limit": limit}
    )

# Function to initialize genre mappings (call this when app starts)
def initialize_genre_mappings(genre_mappings):
    """Initialize genre mappings in the database"""
    # Create genres table if it doesn't exist
    execute_query("""
        CREATE TABLE IF NOT EXISTS genres (
            id SERIAL PRIMARY KEY,
            tmdb_id INTEGER UNIQUE,
            name VARCHAR(100) UNIQUE NOT NULL
        )
    """)
    
    for genre_id, genre_name in genre_mappings.items():
        save_genre_mapping(genre_id, genre_name)
