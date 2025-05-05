import requests
import os
import streamlit as st

# TMDB API configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"

@st.cache_data(ttl=3600)
def get_trending_movies():
    """Fetch trending movies from TMDB API"""
    try:
        url = f"{TMDB_BASE_URL}/trending/movie/week"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        movies = response.json().get('results', [])
        
        # Process movie data
        processed_movies = []
        for movie in movies:
            processed_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'poster_path': f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview'),
                'genre_ids': movie.get('genre_ids', []),
                'original_language': movie.get('original_language')
            }
            processed_movies.append(processed_movie)
        
        return processed_movies
    except Exception as e:
        st.error(f"Error fetching trending movies: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def search_movies(query):
    """Search for movies by query"""
    if not query.strip():
        return []
        
    try:
        url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "query": query,
            "page": 1,
            "include_adult": False
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        movies = response.json().get('results', [])
        
        # Process movie data
        processed_movies = []
        for movie in movies:
            # Skip movies without poster path
            if not movie.get('poster_path'):
                continue
                
            # Get genre names using genre ids
            from movie_data import get_genre_names
            genre_names = get_genre_names(movie.get('genre_ids', []))
            
            processed_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'poster_path': f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date', ''),
                'vote_average': movie.get('vote_average', 0),
                'overview': movie.get('overview', ''),
                'genre_ids': movie.get('genre_ids', []),
                'genres': genre_names,  # Add genre names
                'original_language': movie.get('original_language', '')
            }
            processed_movies.append(processed_movie)
        
        return processed_movies
    except Exception as e:
        st.error(f"Error searching movies: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def get_movie_details(movie_id):
    """Get detailed information about a specific movie"""
    try:
        # First, get basic movie details
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "append_to_response": "credits,videos,recommendations,watch/providers,release_dates"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        movie = response.json()
        
        # Get watch providers (where to stream)
        watch_providers = []
        if movie.get('watch/providers', {}).get('results', {}).get('US', {}):
            providers_data = movie.get('watch/providers', {}).get('results', {}).get('US', {})
            
            # Combine flatrate (subscription), rent, and buy options
            all_providers = []
            for provider_type in ['flatrate', 'rent', 'buy']:
                if providers_data.get(provider_type):
                    all_providers.extend(providers_data.get(provider_type, []))
            
            # Extract unique provider names
            seen_providers = set()
            for provider in all_providers:
                provider_name = provider.get('provider_name')
                if provider_name and provider_name not in seen_providers:
                    watch_providers.append({
                        'name': provider_name,
                        'logo': f"https://image.tmdb.org/t/p/original{provider.get('logo_path')}" if provider.get('logo_path') else None
                    })
                    seen_providers.add(provider_name)
        
        # Get content rating (certification)
        content_rating = "Not Rated"
        if movie.get('release_dates', {}).get('results'):
            for country_data in movie.get('release_dates', {}).get('results', []):
                if country_data.get('iso_3166_1') == 'US':
                    for release in country_data.get('release_dates', []):
                        if release.get('certification'):
                            content_rating = release.get('certification')
                            break
                    break
        
        # Process movie details
        processed_movie = {
            'id': movie.get('id'),
            'title': movie.get('title'),
            'poster_path': f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None,
            'backdrop_path': f"https://image.tmdb.org/t/p/original{movie.get('backdrop_path')}" if movie.get('backdrop_path') else None,
            'release_date': movie.get('release_date'),
            'vote_average': movie.get('vote_average'),
            'runtime': movie.get('runtime'),
            'overview': movie.get('overview'),
            'genres': [genre.get('name') for genre in movie.get('genres', [])],
            'original_language': movie.get('original_language'),
            'production_companies': [company.get('name') for company in movie.get('production_companies', [])],
            'content_rating': content_rating,
            'budget': movie.get('budget'),
            'revenue': movie.get('revenue'),
            'tagline': movie.get('tagline'),
            'watch_providers': watch_providers,
            'cast': [{'name': person.get('name'), 'character': person.get('character')} 
                    for person in movie.get('credits', {}).get('cast', [])[:5]],
            'director': next((person.get('name') for person in movie.get('credits', {}).get('crew', []) 
                             if person.get('job') == 'Director'), 'Unknown'),
            'trailer': next((video.get('key') for video in movie.get('videos', {}).get('results', []) 
                             if video.get('type') == 'Trailer' and video.get('site') == 'YouTube'), None)
        }
        
        return processed_movie
    except Exception as e:
        st.error(f"Error fetching movie details: {str(e)}")
        return {}

@st.cache_data(ttl=3600)
def get_movies_by_preferences(genres, year_range, rating_min, languages):
    """Get movies based on user preferences"""
    try:
        url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "sort_by": "popularity.desc",
            "include_adult": False,
            "include_video": False,
            "page": 1,
            "with_genres": ",".join(map(str, genres)),
            "primary_release_date.gte": f"{year_range[0]}-01-01",
            "primary_release_date.lte": f"{year_range[1]}-12-31",
            "vote_average.gte": rating_min,
            "with_original_language": ",".join(languages) if languages else None
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        movies = response.json().get('results', [])
        
        # Process movie data
        processed_movies = []
        for movie in movies:
            processed_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'poster_path': f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date'),
                'vote_average': movie.get('vote_average'),
                'overview': movie.get('overview'),
                'genre_ids': movie.get('genre_ids', []),
                'original_language': movie.get('original_language')
            }
            processed_movies.append(processed_movie)
        
        return processed_movies
    except Exception as e:
        st.error(f"Error fetching movies by preferences: {str(e)}")
        return []

@st.cache_data(ttl=3600)
def get_similar_movies(movie_id):
    """Get movies similar to a specific movie"""
    if not movie_id:
        return []
        
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}/similar"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "page": 1
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        movies = response.json().get('results', [])
        
        # Process movie data
        processed_movies = []
        for movie in movies:
            # Skip movies without poster path
            if not movie.get('poster_path'):
                continue
                
            # Get genre names using genre ids
            from movie_data import get_genre_names
            genre_names = get_genre_names(movie.get('genre_ids', []))
            
            processed_movie = {
                'id': movie.get('id'),
                'title': movie.get('title'),
                'poster_path': f"{TMDB_IMAGE_BASE_URL}{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'release_date': movie.get('release_date', ''),
                'vote_average': movie.get('vote_average', 0),
                'overview': movie.get('overview', ''),
                'genre_ids': movie.get('genre_ids', []),
                'genres': genre_names,  # Add genre names
                'original_language': movie.get('original_language', '')
            }
            processed_movies.append(processed_movie)
        
        # If API fails, try getting similar movies from database
        if not processed_movies:
            import database as db
            db_similar_movies = db.get_similar_movies_from_db(movie_id)
            if db_similar_movies:
                for movie_data in db_similar_movies:
                    movie = {
                        'id': movie_data[0],  # tmdb_id
                        'title': movie_data[1],
                        'poster_path': movie_data[2],
                        'release_date': movie_data[3],
                        'vote_average': movie_data[4],
                        'genres': movie_data[5].split(',') if movie_data[5] else []
                    }
                    processed_movies.append(movie)
        
        return processed_movies
    except Exception as e:
        st.error(f"Error fetching similar movies: {str(e)}")
        # Try getting similar movies from database as a fallback
        try:
            import database as db
            db_similar_movies = db.get_similar_movies_from_db(movie_id)
            if db_similar_movies:
                processed_movies = []
                for movie_data in db_similar_movies:
                    movie = {
                        'id': movie_data[0],  # tmdb_id
                        'title': movie_data[1],
                        'poster_path': movie_data[2],
                        'release_date': movie_data[3],
                        'vote_average': movie_data[4],
                        'genres': movie_data[5].split(',') if movie_data[5] else []
                    }
                    processed_movies.append(movie)
                return processed_movies
        except Exception:
            pass
        return []
