import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
from tmdb_api import get_movies_by_preferences, get_trending_movies
import streamlit as st

def get_recommendations(preferences):
    """
    Generate movie recommendations based on user preferences
    
    Parameters:
    preferences (dict): Dictionary containing user preferences from the quiz
    
    Returns:
    list: List of recommended movies
    """
    # Extract preferences
    genres = preferences.get('genres', [])
    year_min = preferences.get('year_range', [1990, 2023])[0]
    year_max = preferences.get('year_range', [1990, 2023])[1]
    rating_min = preferences.get('min_rating', 7.0)
    languages = preferences.get('languages', ['en'])
    
    # Get movies based on preferences
    recommended_movies = get_movies_by_preferences(
        genres=genres,
        year_range=[year_min, year_max],
        rating_min=rating_min,
        languages=languages
    )
    
    # If we don't have enough recommendations, get trending movies
    if len(recommended_movies) < 8:
        trending_movies = get_trending_movies()
        # Filter trending movies by preferences
        trending_filtered = [
            movie for movie in trending_movies
            if (not genres or any(genre_id in movie.get('genre_ids', []) for genre_id in genres)) and
               (not languages or movie.get('original_language') in languages) and
               (movie.get('vote_average', 0) >= rating_min)
        ]
        recommended_movies.extend(trending_filtered)
        
        # Remove duplicates
        seen_ids = set()
        unique_recommendations = []
        for movie in recommended_movies:
            if movie['id'] not in seen_ids:
                seen_ids.add(movie['id'])
                unique_recommendations.append(movie)
        
        recommended_movies = unique_recommendations
    
    # Use content-based filtering to rank the recommendations
    return rank_recommendations(recommended_movies, preferences)

def rank_recommendations(movies, preferences):
    """
    Rank recommendations using a content-based approach
    
    Parameters:
    movies (list): List of movie dictionaries
    preferences (dict): User preferences
    
    Returns:
    list: Ranked list of movies
    """
    if not movies:
        return []
    
    # Create a feature matrix for movies
    features = []
    
    preferred_genres = preferences.get('genres', [])
    preferred_year_range = preferences.get('year_range', [1990, 2023])
    preferred_rating = preferences.get('min_rating', 7.0)
    
    # Average year from the range
    target_year = sum(preferred_year_range) / 2
    
    for movie in movies:
        # Extract release year
        release_year = 2022  # Default value
        if movie.get('release_date'):
            try:
                release_year = int(movie.get('release_date', '2022')[:4])
            except (ValueError, TypeError):
                pass
        
        # Calculate year proximity (normalized)
        year_proximity = 1 - min(abs(release_year - target_year) / 50, 1)
        
        # Calculate genre match
        movie_genre_ids = movie.get('genre_ids', [])
        genre_match = len(set(movie_genre_ids).intersection(set(preferred_genres))) / max(len(preferred_genres), 1) if preferred_genres else 0.5
        
        # Calculate rating score
        rating_score = min(movie.get('vote_average', 0) / 10, 1)
        
        # Popularity bias (more recent movies get a slight boost)
        recency_boost = min((2023 - preferred_year_range[0]) / (2023 - preferred_year_range[0] + 1), 0.2) if release_year >= preferred_year_range[0] else 0
        
        # Combine features
        feature_vector = [
            genre_match * 0.5,  # Genre match has high weight
            year_proximity * 0.3,  # Year proximity has medium weight
            rating_score * 0.2,  # Rating has lower weight
            recency_boost  # Small recency boost
        ]
        
        features.append(feature_vector)
    
    # Calculate similarity score
    if features:
        # Normalize features
        scaler = MinMaxScaler()
        features_normalized = scaler.fit_transform(features)
        
        # Calculate a compound score for each movie
        scores = [sum(feature) for feature in features_normalized]
        
        # Sort movies by score (descending)
        movies_with_scores = list(zip(movies, scores))
        ranked_movies = [movie for movie, _ in sorted(movies_with_scores, key=lambda x: x[1], reverse=True)]
        
        return ranked_movies
    
    return movies
