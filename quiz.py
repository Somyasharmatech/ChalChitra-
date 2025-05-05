import streamlit as st
from recommendation_engine import get_recommendations
from movie_data import get_all_genres, get_genre_ids, get_languages, get_language_code
import database as db
import uuid

# Ensure we have a session ID for the current user
def ensure_session_id():
    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    return st.session_state.session_id

# Get or create user in database
def get_or_create_user():
    session_id = ensure_session_id()
    user_id = db.get_or_create_user(session_id)
    if not user_id:
        st.error("Failed to create or retrieve user profile.")
    return user_id

def display_quiz():
    """Display the 5-question preference quiz"""
    st.header("Tell us what you like")
    st.markdown("Answer these 5 questions to get personalized movie recommendations")
    
    # If user has saved preferences, load them from database
    user_id = get_or_create_user()
    saved_preferences = {}
    
    if user_id:
        saved_preferences = db.get_user_preferences(user_id)
    
    with st.form("preference_quiz"):
        # Question 1: Favorite genres
        st.subheader("1. What genres do you enjoy?")
        all_genres = get_all_genres()
        
        # Get default genres if available
        default_genres = []
        if saved_preferences and 'genres' in saved_preferences:
            genre_names = [name for name, id in zip(all_genres, get_genre_ids(all_genres)) 
                         if id in saved_preferences['genres']]
            default_genres = genre_names
        
        selected_genres = st.multiselect(
            "Select up to 3 genres",
            options=all_genres,
            default=default_genres
        )
        
        # Question 2: Preferred release years
        st.subheader("2. What era of movies do you prefer?")
        default_years = (2000, 2023)
        if saved_preferences and 'year_range' in saved_preferences:
            default_years = saved_preferences['year_range']
            
        year_range = st.slider(
            "Select a range of years",
            1970, 2023, default_years
        )
        
        # Question 3: Minimum rating
        st.subheader("3. What's your minimum acceptable rating?")
        default_rating = 7.0
        if saved_preferences and 'min_rating' in saved_preferences:
            default_rating = saved_preferences['min_rating']
            
        min_rating = st.slider(
            "Select minimum rating (out of 10)",
            0.0, 10.0, default_rating, 0.5
        )
        
        # Question 4: Movie language preference
        st.subheader("4. Do you have a language preference?")
        languages = get_languages()
        
        # Get default languages if available
        default_langs = ["English (en)"]
        if saved_preferences and 'languages' in saved_preferences:
            saved_langs = saved_preferences['languages']
            lang_dict = {get_language_code(lang): lang for lang in languages}
            default_langs = [lang_dict.get(code, "English (en)") for code in saved_langs if code in lang_dict]
            
        selected_languages = st.multiselect(
            "Select languages (leave empty for all)",
            options=languages,
            default=default_langs
        )
        
        # Question 5: Movie length preference
        st.subheader("5. Do you prefer shorter or longer movies?")
        
        # Get default movie length if available
        default_length = "No preference"
        if saved_preferences and 'runtime_range' in saved_preferences:
            runtime = saved_preferences['runtime_range']
            if runtime and len(runtime) == 2:
                if runtime[1] <= 90:
                    default_length = "Short (< 90 min)"
                elif runtime[0] >= 120:
                    default_length = "Long (> 120 min)"
                else:
                    default_length = "Medium (90-120 min)"
            
        movie_length = st.radio(
            "Select your preference",
            options=["Short (< 90 min)", "Medium (90-120 min)", "Long (> 120 min)", "No preference"],
            index=["Short (< 90 min)", "Medium (90-120 min)", "Long (> 120 min)", "No preference"].index(default_length)
        )
        
        # Submit button
        submitted = st.form_submit_button("Get Recommendations")
        
        if submitted:
            # Process form results
            process_quiz_results(selected_genres, year_range, min_rating, selected_languages, movie_length)

def process_quiz_results(genres, year_range, min_rating, languages, movie_length):
    """Process quiz results and update session state with preferences"""
    # Convert genre names to IDs
    genre_ids = get_genre_ids(genres)
    
    # Extract language codes
    language_codes = [get_language_code(lang) for lang in languages]
    
    # Determine runtime filter based on movie length preference
    runtime_range = None
    if movie_length == "Short (< 90 min)":
        runtime_range = [0, 90]
    elif movie_length == "Medium (90-120 min)":
        runtime_range = [90, 120]
    elif movie_length == "Long (> 120 min)":
        runtime_range = [120, 300]
    
    # Store preferences in session state
    st.session_state.preferences = {
        'genres': genre_ids,
        'year_range': year_range,
        'min_rating': min_rating,
        'languages': language_codes,
        'runtime_range': runtime_range
    }
    
    # Save preferences to database
    user_id = get_or_create_user()
    if user_id:
        db.save_user_preferences(user_id, st.session_state.preferences)
    
    # Mark quiz as completed
    st.session_state.quiz_completed = True
    
    # Generate recommendations based on preferences
    recommendations = get_recommendations(st.session_state.preferences)
    
    # Save recommended movies to database
    if user_id:
        for movie in recommendations[:20]:  # Limit to first 20 recommendations
            db.save_movie(movie)
    
    # Store recommendations in session state
    st.session_state.movies_data = recommendations
    
    # Show success message
    st.success("Preferences saved! We've found some movies for you.")
    
    # Refresh page to show recommendations
    st.rerun()
