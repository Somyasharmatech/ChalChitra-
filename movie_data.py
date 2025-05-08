import streamlit as st
import requests
import os

import database as db

# TMDB API configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

# Fallback genre mapping if API fails
FALLBACK_GENRES = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western"
}

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_genres_mapping():
    """Get a mapping of genre IDs to genre names from TMDB API"""
    try:
        url = f"{TMDB_BASE_URL}/genre/movie/list"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        genres = response.json().get('genres', [])
        
        # Create mappings
        id_to_name = {genre['id']: genre['name'] for genre in genres}
        name_to_id = {genre['name']: genre['id'] for genre in genres}
        
        # Save genre mappings to database
        for genre_id, genre_name in id_to_name.items():
            db.save_genre_mapping(genre_id, genre_name)
        
        return id_to_name, name_to_id
    except Exception as e:
        st.error(f"Error fetching genres: {str(e)}")
        # Use fallback genres
        id_to_name = FALLBACK_GENRES
        name_to_id = {v: k for k, v in FALLBACK_GENRES.items()}
        
        # Save fallback mappings to database
        for genre_id, genre_name in id_to_name.items():
            db.save_genre_mapping(genre_id, genre_name)
            
        return id_to_name, name_to_id

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_all_genres():
    """Get a list of all movie genres"""
    try:
        _, name_to_id = get_genres_mapping()
        return sorted(list(name_to_id.keys()))
    except Exception as e:
        st.error(f"Error getting genres list: {str(e)}")
        return []

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_genre_ids(genre_names):
    """Convert genre names to genre IDs"""
    try:
        _, name_to_id = get_genres_mapping()
        return [name_to_id.get(name) for name in genre_names if name in name_to_id]
    except Exception as e:
        st.error(f"Error getting genre IDs: {str(e)}")
        return []

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_genre_names(genre_ids):
    """Convert genre IDs to genre names"""
    try:
        id_to_name, _ = get_genres_mapping()
        return [id_to_name.get(genre_id) for genre_id in genre_ids if genre_id in id_to_name]
    except Exception as e:
        st.error(f"Error getting genre names: {str(e)}")
        return []

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_languages():
    """Get a list of common movie languages"""
    # Dictionary of ISO 639-1 language codes and their English names
    language_dict = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "zh": "Chinese",
        "hi": "Hindi",
        "ru": "Russian",
        "pt": "Portuguese",
        "sv": "Swedish",
        "nl": "Dutch",
        "da": "Danish",
        "no": "Norwegian"
    }
    
    return [f"{v} ({k})" for k, v in sorted(language_dict.items(), key=lambda x: x[1])]

@st.cache_data(ttl=86400)  # Cache for 24 hours
def get_language_code(language_display):
    """Extract language code from display format"""
    if not language_display or "(" not in language_display or ")" not in language_display:
        return "en"  # Default to English
    
    try:
        # Extract code from format "Language Name (code)"
        return language_display.split("(")[1].split(")")[0].strip()
    except (IndexError, AttributeError):
        return "en"  # Default to English
