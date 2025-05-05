import streamlit as st
import pandas as pd
import os
import base64
from tmdb_api import get_trending_movies, search_movies, get_movie_details, get_similar_movies
from recommendation_engine import get_recommendations
from movie_data import get_all_genres, get_languages
from quiz import display_quiz, process_quiz_results, get_or_create_user, ensure_session_id
from utils import display_movie_card, display_movie_details, add_custom_css
import database as db
from login import authenticate

# Page configuration
st.set_page_config(
    page_title="ChalChitra",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add custom CSS for Netflix-inspired styling
add_custom_css()

# Initialize genre mappings in the database
from movie_data import FALLBACK_GENRES
db.initialize_genre_mappings(FALLBACK_GENRES)

# Netflix-like intro sound function
def get_netflix_intro_sound():
    # Netflix-like intro sound in base64 (sourced from an audio file)
    audio_base64 = "SUQzBAAAAAABE1RJVDIAAAAZAAAATmV0ZmxpeCBJbnRybyBTb3VuZCBFZmZlY3RUWUVSAAAAGQAAAGh0dHBzOi8vd3d3LnlvdXR1YmUuY29tL1RBTEIAAAAWAAAATWF5IGJlIGNvcHlyaWdodGVkIHNvdW5kQ09NTQAAAA8AAABlbmcAU291bmQgRWZmZWN0QVJUAAAAABAAAAE5ZXRmbGl4IFN0dWRpb3NUUEUxAAAADQAAAE5ldGZsaXggSW50cm8AAP/7kGQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAEluZm8AAAAPAAAACQAADuAACgoKFBQUHx8fKioqNDQ0Pz8/SUlJVFRUXl5eaWlpc3Nzfn5+iIiIk5OTnZ2dqKios7OzvLy8xsbG0dHR29vb5OTk7u7u9/f3AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/+xZUAAAAGkDBAQDCyAAAAszMAAAARgAABwAAAImAAATCSL0YO4IAAD/+5JkAA/wAABpAAAACAAADSAAAAEAAAGkAAAAIAAANIAAAAQAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAA0gAAAAAAAAFBYCgQCA18HeHh4eHh4eKfD4fL/Lw+Xy+eDweDj+XhQKBQLssBAIBAIFAgFKgUWCgcDmgIFApssdMKn/9/KBAQEBAQwIYEOEOEQEOsyggICAgIeXDiWrAwMDnAwMDAwMDAwMDAwMDA0PDw8QCAgICAgICAgICA0PDw8PDwwMDAwMDAwMDAwMDwwMDAwMDAwMDAwMdmZlQUFBQUFBQUFBQY//D/8UFDQ0NFQ0ND/8aioqGqqqqaqqqKxVTEFNRTMuOTkuNVVVVYPjFUSVVVQEAQD/5P//qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqv/7kmRAj/AAAGkAAAAIAAANIAAAAQAAAaQAAAAgAAA0gAAABKqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq"
    return f'<audio autoplay="true"><source src="data:audio/mpeg;base64,{audio_base64}" type="audio/mpeg"></audio>'

# Initialize session state
if 'preferences' not in st.session_state:
    st.session_state.preferences = {}
if 'quiz_completed' not in st.session_state:
    st.session_state.quiz_completed = False
if 'movies_data' not in st.session_state:
    st.session_state.movies_data = []
if 'played_intro' not in st.session_state:
    st.session_state.played_intro = False
    
# Play Netflix-like intro sound on first load
if not st.session_state.played_intro:
    st.markdown(get_netflix_intro_sound(), unsafe_allow_html=True)
    st.session_state.played_intro = True
    
# Handle navigation based on query parameters
query_params = st.experimental_get_query_params()
current_view = "home"
selected_movie = None

if "view" in query_params:
    current_view = query_params["view"][0]
    
if "movie_id" in query_params and current_view == "details":
    try:
        selected_movie = int(query_params["movie_id"][0])
    except (ValueError, TypeError):
        selected_movie = None

# Check if user is authenticated
is_authenticated = authenticate()

# If not authenticated, stop execution
if not is_authenticated:
    st.stop()

# Ensure user session is created
session_id = ensure_session_id()
user_id = st.session_state.user_id if st.session_state.is_authenticated else get_or_create_user()

# Load preferences from database if available but not in session state
if user_id and not st.session_state.quiz_completed:
    saved_preferences = db.get_user_preferences(user_id)
    if saved_preferences and 'genres' in saved_preferences:
        st.session_state.preferences = saved_preferences
        st.session_state.quiz_completed = True
        # Generate recommendations based on saved preferences
        recommendations = get_recommendations(saved_preferences)
        st.session_state.movies_data = recommendations

# Header
st.title("ChalChitra")
st.markdown("### Discover movies tailored to your taste")

# Sidebar for filters and controls
with st.sidebar:
    st.header("Filters")
    
    # Search box
    search_query = st.text_input("Search for movies", "")
    
    # Initialize filter variables
    selected_genre = "All Genres"
    selected_language = "All Languages"
    
    if st.session_state.quiz_completed:
        # Genre filter
        genres = get_all_genres()
        selected_genre = st.selectbox("Filter by genre", ["All Genres"] + genres)
        
        # Language filter
        languages = get_languages()
        selected_language = st.selectbox("Filter by language", ["All Languages"] + languages)
        
        # Reset preferences button
        if st.button("Reset Preferences"):
            if user_id:
                # Clear preferences in database
                db.execute_query(
                    "DELETE FROM user_preferences WHERE user_id = :user_id",
                    {"user_id": user_id}
                )
                db.execute_query(
                    "DELETE FROM user_genre_preferences WHERE user_id = :user_id",
                    {"user_id": user_id}
                )
                
            st.session_state.preferences = {}
            st.session_state.quiz_completed = False
            st.session_state.movies_data = []
            st.session_state.current_view = "home"
            st.rerun()
    
    # About section
    st.markdown("---")
    st.markdown("### About")
    st.markdown("This app recommends movies based on your preferences using data from TMDB, with personalized recommendations saved to a database.")
    
    # API Key notice
    st.markdown("---")
    st.markdown("### API Notice")
    
    if not os.getenv("TMDB_API_KEY"):
        st.warning("""
        **TMDB API Key Required**
        
        To access live movie data, you need to add a TMDB API key. Without this key, the app can use only data stored in the database.
        
        To get a free API key:
        1. Sign up at [themoviedb.org](https://www.themoviedb.org/signup)
        2. Go to Settings → API and request an API key
        3. Add the key as an environment variable named `TMDB_API_KEY`
        """)
    else:
        st.success("TMDB API Key is configured correctly.")

# Define a function to set query parameters
def set_query_params(view, movie_id=None):
    params = {"view": view}
    if movie_id is not None:
        params["movie_id"] = str(movie_id)
    st.experimental_set_query_params(**params)

# Main content area
if current_view == "home":
    if not st.session_state.quiz_completed:
        # Display quiz
        display_quiz()
    else:
        # Tabs for different movie categories
        tab1, tab2, tab3, tab4 = st.tabs(["Recommended For You", "Trending", "Similar Movies", "Your History"])
        
        with tab1:
            st.header("Recommended For You")
            
            # Apply filters to recommendations
            filtered_movies = st.session_state.movies_data
            
            if search_query:
                search_results = search_movies(search_query)
                st.write(f"Search results for '{search_query}'")
                if search_results:
                    cols = st.columns(4)
                    for idx, movie in enumerate(search_results[:8]):
                        with cols[idx % 4]:
                            # Add URL to movie card for details
                            if st.button(f"View: {movie['title'][:20]}...", key=f"search_{movie['id']}"):
                                # Mark movie as watched when viewing details
                                user_id = get_or_create_user()
                                if user_id:
                                    db.save_watched_movie(user_id, movie)
                                
                                # Set query params and rerun
                                set_query_params("details", movie['id'])
                                st.rerun()
                            
                            # Display movie card
                            st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                    width=150, 
                                    caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
                else:
                    st.write("No results found.")
            else:
                # Apply genre filter if selected
                if selected_genre != "All Genres":
                    filtered_movies = [m for m in filtered_movies if selected_genre in m.get('genres', [])]
                
                # Apply language filter if selected
                if selected_language != "All Languages":
                    # Extract language code from display format (e.g., "English (en)" -> "en")
                    language_code = selected_language.split("(")[-1].replace(")", "").strip() if "(" in selected_language else selected_language
                    filtered_movies = [m for m in filtered_movies if m.get('original_language') == language_code]
                
                if filtered_movies:
                    # Display movies in a grid layout
                    cols = st.columns(4)
                    for idx, movie in enumerate(filtered_movies[:8]):
                        with cols[idx % 4]:
                            # Add URL to movie card for details
                            if st.button(f"View: {movie['title'][:20]}...", key=f"rec_{movie['id']}"):
                                # Mark movie as watched when viewing details
                                user_id = get_or_create_user()
                                if user_id:
                                    db.save_watched_movie(user_id, movie)
                                
                                # Set query params and rerun
                                set_query_params("details", movie['id'])
                                st.rerun()
                            
                            # Display movie card
                            st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                    width=150, 
                                    caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
                else:
                    st.write("No movies match your filters. Try adjusting your preferences.")
        
        with tab2:
            st.header("Trending Movies")
            trending_movies = get_trending_movies()
            
            if trending_movies:
                cols = st.columns(4)
                for idx, movie in enumerate(trending_movies[:8]):
                    with cols[idx % 4]:
                        # Add URL to movie card for details
                        if st.button(f"View: {movie['title'][:20]}...", key=f"trend_{movie['id']}"):
                            # Mark movie as watched when viewing details
                            user_id = get_or_create_user()
                            if user_id:
                                db.save_watched_movie(user_id, movie)
                            
                            # Set query params and rerun
                            set_query_params("details", movie['id'])
                            st.rerun()
                        
                        # Display movie card
                        st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                width=150, 
                                caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
        
        with tab3:
            st.header("You Might Also Like")
            if st.session_state.movies_data:
                # Show similar movies based on the first recommendation
                similar_movies = get_similar_movies(st.session_state.movies_data[0]['id'])
                
                if similar_movies:
                    cols = st.columns(4)
                    for idx, movie in enumerate(similar_movies[:8]):
                        with cols[idx % 4]:
                            # Add URL to movie card for details
                            if st.button(f"View: {movie['title'][:20]}...", key=f"sim_{movie['id']}"):
                                # Mark movie as watched when viewing details
                                user_id = get_or_create_user()
                                if user_id:
                                    db.save_watched_movie(user_id, movie)
                                
                                # Set query params and rerun
                                set_query_params("details", movie['id'])
                                st.rerun()
                            
                            # Display movie card
                            st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                    width=150, 
                                    caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
                else:
                    st.write("No similar movies found.")
            else:
                st.write("Complete the preference quiz to get recommendations.")
                
        with tab4:
            st.header("Your History")
            
            if user_id:
                try:
                    # Get user's rated movies
                    user_ratings = db.get_user_movie_ratings(user_id)
                    
                    # Get user's watched movies
                    watched_movies = db.get_user_watched_movies(user_id)
                    
                    # Combine information from both sources - watched and rated
                    if user_ratings:
                        st.subheader("Movies You've Rated")
                        
                        try:
                            # Convert to DataFrame for easier display
                            ratings_df = pd.DataFrame(user_ratings, columns=[
                                'tmdb_id', 'title', 'poster_path', 'release_date', 'vote_average', 'your_rating'
                            ])
                            
                            # Display user ratings as a table
                            st.dataframe(
                                ratings_df[['title', 'release_date', 'vote_average', 'your_rating']],
                                column_config={
                                    "title": "Movie Title",
                                    "release_date": st.column_config.DateColumn("Release Date"),
                                    "vote_average": st.column_config.NumberColumn("TMDB Rating", format="%.1f ⭐"),
                                    "your_rating": st.column_config.NumberColumn("Your Rating", format="%d ⭐"),
                                },
                                use_container_width=True,
                                hide_index=True
                            )
                        except Exception as e:
                            st.warning(f"Unable to display ratings table: {str(e)}")
                        
                        # Display rated movies as cards
                        st.subheader("Your Rated Movies")
                        rated_movies = []
                        for rating in user_ratings:
                            try:
                                movie = {
                                    'id': rating[0],  # tmdb_id
                                    'title': rating[1],
                                    'poster_path': rating[2],
                                    'release_date': rating[3],
                                    'vote_average': rating[4],
                                    'user_rating': rating[5]
                                }
                                rated_movies.append(movie)
                            except IndexError:
                                continue
                        
                        if rated_movies:
                            cols = st.columns(4)
                            for idx, movie in enumerate(rated_movies[:8]):
                                with cols[idx % 4]:
                                    # Add URL to movie card for details
                                    if st.button(f"View: {movie['title'][:20]}...", key=f"rated_{movie['id']}"):
                                        # Set query params and rerun
                                        set_query_params("details", movie['id'])
                                        st.rerun()
                                    
                                    # Display movie card
                                    st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                            width=150, 
                                            caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}\nYour rating: {movie.get('user_rating')}/10")
                    
                    # Display watched movies
                    if watched_movies:
                        st.subheader("Your Watch History")
                        
                        watched_movie_list = []
                        for movie_data in watched_movies:
                            try:
                                movie = {
                                    'id': movie_data[0],  # tmdb_id
                                    'title': movie_data[1],
                                    'poster_path': movie_data[2],
                                    'release_date': movie_data[3],
                                    'vote_average': movie_data[4]
                                }
                                watched_movie_list.append(movie)
                            except IndexError:
                                continue
                        
                        if watched_movie_list:
                            cols = st.columns(4)
                            for idx, movie in enumerate(watched_movie_list[:8]):
                                with cols[idx % 4]:
                                    # Add URL to movie card for details
                                    if st.button(f"View: {movie['title'][:20]}...", key=f"watched_{movie['id']}"):
                                        # Set query params and rerun
                                        set_query_params("details", movie['id'])
                                        st.rerun()
                                    
                                    # Display movie card
                                    st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                            width=150, 
                                            caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
                    
                    # Get movies from database that are popular with users
                    db_popular_movies = db.get_popular_movies_from_db()
                    
                    if db_popular_movies:
                        st.subheader("Popular Among Users")
                        popular_movies = []
                        for movie_data in db_popular_movies:
                            try:
                                movie = {
                                    'id': movie_data[0],  # tmdb_id
                                    'title': movie_data[1],
                                    'poster_path': movie_data[2],
                                    'release_date': movie_data[3],
                                    'vote_average': movie_data[4],
                                    'rating_count': movie_data[5],
                                    'avg_rating': movie_data[6]
                                }
                                popular_movies.append(movie)
                            except IndexError:
                                continue
                        
                        if popular_movies:
                            cols = st.columns(4)
                            for idx, movie in enumerate(popular_movies[:4]):
                                with cols[idx % 4]:
                                    # Add URL to movie card for details
                                    if st.button(f"View: {movie['title'][:20]}...", key=f"popular_{movie['id']}"):
                                        # Set query params and rerun
                                        set_query_params("details", movie['id'])
                                        st.rerun()
                                    
                                    # Display movie card
                                    st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                                            width=150, 
                                            caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}\nUser Rating: {movie.get('avg_rating', 0):.1f} ({movie.get('rating_count', 0)} ratings)")
                    
                    if not user_ratings and not watched_movies and not db_popular_movies:
                        st.info("You haven't watched or rated any movies yet. Watch movies to see them appear here!")
                
                except Exception as e:
                    st.error(f"Error retrieving user history: {str(e)}")
                    st.info("Try exploring some movies and rating them to build your history!")
            else:
                st.error("Unable to retrieve user history. Please refresh the page or log in.")

elif current_view == "details":
    # Back button
    if st.button("← Back to Recommendations"):
        # Back to home view
        set_query_params("home")
        st.rerun()
    
    # Display detailed view of selected movie
    if selected_movie:
        movie_details = get_movie_details(selected_movie)
        display_movie_details(movie_details)
        
        # Similar movies section
        st.subheader("Similar Movies")
        similar_movies = get_similar_movies(selected_movie)
        
        if similar_movies:
            cols = st.columns(4)
            for idx, movie in enumerate(similar_movies[:4]):
                with cols[idx % 4]:
                    # Add URL to movie card for details
                    if st.button(f"View: {movie['title'][:20]}...", key=f"similar_{movie['id']}"):
                        # Mark movie as watched when viewing details
                        user_id = get_or_create_user()
                        if user_id:
                            db.save_watched_movie(user_id, movie)
                        
                        # Set query params and rerun
                        set_query_params("details", movie['id'])
                        st.rerun()
                    
                    # Display movie card
                    st.image(movie.get('poster_path', "https://via.placeholder.com/200x300?text=No+Image"), 
                            width=150, 
                            caption=f"{movie.get('title')} ({movie.get('release_date', '')[:4]})\n★ {movie.get('vote_average', 0):.1f}")
