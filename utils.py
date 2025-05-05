import streamlit as st
from movie_data import get_genre_names
import random

def add_custom_css():
    """Add custom CSS to style the app with Netflix-inspired theme"""
    st.markdown("""
    <style>
    /* Netflix-inspired styling */
    .movie-card {
        background-color: #221F1F;
        border-radius: 5px;
        padding: 10px;
        margin-bottom: 20px;
        transition: transform 0.3s;
    }
    
    .movie-card:hover {
        transform: scale(1.05);
        cursor: pointer;
    }
    
    .movie-poster {
        width: 100%;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    
    .movie-title {
        font-weight: bold;
        margin-bottom: 5px;
    }
    
    .movie-rating {
        color: #E50914;
        font-weight: bold;
    }
    
    .movie-year {
        color: #ccc;
        font-size: 0.9em;
    }
    
    .movie-genre {
        color: #aaa;
        font-size: 0.8em;
    }
    
    .movie-user-rating {
        color: #E50914;
        font-weight: bold;
        font-size: 0.9em;
        margin-top: 2px;
    }
    
    /* Movie details page */
    .movie-backdrop {
        width: 100%;
        height: 300px;
        object-fit: cover;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    .movie-info {
        display: flex;
        margin-bottom: 20px;
    }
    
    .movie-detail-poster {
        width: 200px;
        border-radius: 5px;
        margin-right: 20px;
    }
    
    .movie-details {
        flex: 1;
    }
    
    .movie-overview {
        margin-bottom: 20px;
        line-height: 1.5;
    }
    
    .movie-meta {
        display: flex;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }
    
    .movie-meta-item {
        margin-right: 20px;
        margin-bottom: 10px;
    }
    
    .movie-meta-label {
        font-weight: bold;
        color: #aaa;
    }
    
    .movie-meta-value {
        color: white;
    }
    
    .movie-cast {
        margin-top: 20px;
    }
    
    .movie-cast-item {
        margin-bottom: 5px;
    }
    
    /* Custom button styling */
    .stButton button {
        background-color: #E50914;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 8px 16px;
        transition: background-color 0.3s;
    }
    
    .stButton button:hover {
        background-color: #B20710;
    }
    
    /* Custom tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        font-size: 16px;
        font-weight: 500;
        color: #ccc;
        border-radius: 4px 4px 0 0;
    }
    
    .stTabs [aria-selected="true"] {
        color: white;
        background-color: transparent;
        border-bottom: 3px solid #E50914;
    }
    </style>
    """, unsafe_allow_html=True)

def display_movie_card(movie):
    """Display a movie card with poster, title, rating, and release year"""
    # Use one of the pre-fetched stock photos if no poster is available
    poster_url = movie.get('poster_path')
    if not poster_url:
        stock_posters = [
            "https://images.unsplash.com/photo-1626814026160-2237a95fc5a0",
            "https://images.unsplash.com/photo-1572188863110-46d457c9234d",
            "https://images.unsplash.com/photo-1536440136628-849c177e76a1",
            "https://images.unsplash.com/photo-1572988276585-71035689a285",
            "https://images.unsplash.com/photo-1623116135518-7953c5038f5b",
            "https://images.unsplash.com/photo-1440404653325-ab127d49abc1",
            "https://images.unsplash.com/photo-1509347528160-9a9e33742cdb",
            "https://images.unsplash.com/photo-1569793667639-dae11573b34f"
        ]
        poster_url = random.choice(stock_posters)
    
    # Extract release year
    release_year = "Unknown"
    if movie.get('release_date'):
        try:
            release_year = movie.get('release_date', '')[:4]
        except (IndexError, TypeError):
            pass
    
    # Convert genre IDs to names if needed
    genre_names = []
    if 'genre_ids' in movie:
        genre_names = get_genre_names(movie.get('genre_ids', []))
    elif 'genres' in movie:
        genre_names = movie.get('genres', [])
        
    # Show only first 2 genres
    if genre_names:
        genres_display = ", ".join([str(g) for g in genre_names[:2]])
    else:
        genres_display = ""
    
    # Movie rating (TMDB rating)
    rating = movie.get('vote_average', 0)
    
    # User rating if available
    user_rating = movie.get('user_rating')
    user_rating_display = f"<div class='movie-user-rating'>Your Rating: {user_rating}★</div>" if user_rating else ""
    
    # Create clickable card
    card_html = f"""
    <div class="movie-card" onclick="handleClick({movie['id']})">
        <img src="{poster_url}" class="movie-poster" alt="{movie['title']} poster">
        <div class="movie-title">{movie['title']}</div>
        <div class="movie-rating">★ {rating:.1f}</div>
        {user_rating_display}
        <div class="movie-year">{release_year}</div>
        <div class="movie-genre">{genres_display}</div>
    </div>
    """
    
    # Add view details button to the HTML
    import random
    import time
    unique_key = f"btn_{movie['id']}_{random.randint(1000, 9999)}_{int(time.time())}"
    
    # Use a form to handle the button click properly
    with st.form(key=f"form_{unique_key}"):
        st.markdown(card_html, unsafe_allow_html=True)
        submit_button = st.form_submit_button(f"View Details: {movie['title']}")
        
        if submit_button:
            # Import here to avoid circular imports
            from quiz import get_or_create_user
            import database as db
            
            # Mark movie as watched when viewing details
            user_id = get_or_create_user()
            if user_id:
                db.save_watched_movie(user_id, movie)
                
            # Navigate to details page
            st.session_state.selected_movie = movie['id']
            st.session_state.current_view = "details"
            st.rerun()

def display_movie_details(movie):
    """Display detailed view of a movie with enhanced information"""
    # Background image
    if movie.get('backdrop_path'):
        backdrop_url = movie.get('backdrop_path')
    else:
        # Use one of the stock cinema backgrounds
        cinema_backgrounds = [
            "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba",
            "https://images.unsplash.com/photo-1682872368723-e292c23b364f",
            "https://images.unsplash.com/photo-1738193026574-cfbcccbeb052"
        ]
        backdrop_url = random.choice(cinema_backgrounds)
    
    st.markdown(f'<img src="{backdrop_url}" class="movie-backdrop" alt="Movie backdrop">', unsafe_allow_html=True)
    
    # Movie info section
    col1, col2 = st.columns([1, 3])
    
    with col1:
        poster_url = movie.get('poster_path', "https://images.unsplash.com/photo-1572188863110-46d457c9234d")
        st.markdown(f'<img src="{poster_url}" class="movie-detail-poster" alt="{movie["title"]} poster">', unsafe_allow_html=True)
        
        # Add "Where to Watch" information
        watch_providers = movie.get('watch_providers', [])
        if watch_providers:
            providers_html = '<div class="where-to-watch"><h4>Where to Watch</h4><ul class="streaming-services">'
            for provider in watch_providers:
                provider_logo = provider.get('logo', '')
                provider_name = provider.get('name', '')
                if provider_logo:
                    providers_html += f'<li class="provider-item"><img src="{provider_logo}" alt="{provider_name}" class="provider-logo"><span class="provider-name">{provider_name}</span></li>'
                else:
                    providers_html += f'<li class="provider-item"><span class="provider-name">{provider_name}</span></li>'
            providers_html += '</ul>'
            
            # Add tagline if available
            if movie.get('tagline'):
                providers_html += f'<div class="movie-tagline">"{movie.get("tagline")}"</div>'
                
            # Add content rating if available
            if movie.get('content_rating') and movie.get('content_rating') != "Not Rated":
                providers_html += f'<div class="content-rating"><span class="rating-badge">{movie.get("content_rating")}</span></div>'
            
            providers_html += '</div>'
            st.markdown(providers_html, unsafe_allow_html=True)
        else:
            # Fallback to search links if no watch provider data
            st.markdown("""
            <div class="where-to-watch">
                <h4>Find This Movie</h4>
                <ul class="streaming-services">
                    <li><a href="https://www.netflix.com/search?q={title}" target="_blank">Netflix</a></li>
                    <li><a href="https://www.primevideo.com/search?k={title}" target="_blank">Amazon Prime</a></li>
                    <li><a href="https://www.disneyplus.com/" target="_blank">Disney+</a></li>
                    <li><a href="https://www.hulu.com/search?q={title}" target="_blank">Hulu</a></li>
                    <li><a href="https://www.max.com/search" target="_blank">Max (HBO)</a></li>
                </ul>
                <p class="streaming-note">Click links to search for this movie on streaming platforms</p>
            </div>
            """.format(title=movie.get('title', 'Unknown')), unsafe_allow_html=True)
            
            # Add tagline if available even if no providers
            if movie.get('tagline'):
                st.markdown(f'<div class="movie-tagline">"{movie.get("tagline")}"</div>', unsafe_allow_html=True)
                
            # Add content rating if available
            if movie.get('content_rating') and movie.get('content_rating') != "Not Rated":
                st.markdown(f'<div class="content-rating"><span class="rating-badge">{movie.get("content_rating")}</span></div>', unsafe_allow_html=True)
    
    with col2:
        st.header(movie.get('title', 'Unknown Title'))
        
        # Release year, runtime, rating with more detail
        meta_html = '<div class="movie-meta">'
        if movie.get('release_date'):
            release_date = movie.get("release_date", "Unknown")
            # Format release date for better display
            try:
                from datetime import datetime
                release_datetime = datetime.strptime(release_date, "%Y-%m-%d")
                formatted_date = release_datetime.strftime("%B %d, %Y")
                meta_html += f'<div class="movie-meta-item"><span class="movie-meta-label">Released:</span> <span class="movie-meta-value">{formatted_date}</span></div>'
            except:
                meta_html += f'<div class="movie-meta-item"><span class="movie-meta-label">Released:</span> <span class="movie-meta-value">{release_date}</span></div>'
        
        if movie.get('runtime'):
            hours = movie.get('runtime', 0) // 60
            minutes = movie.get('runtime', 0) % 60
            runtime_display = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            meta_html += f'<div class="movie-meta-item"><span class="movie-meta-label">Runtime:</span> <span class="movie-meta-value">{runtime_display}</span></div>'
        
        if movie.get('vote_average') is not None:
            meta_html += f'<div class="movie-meta-item"><span class="movie-meta-label">Rating:</span> <span class="movie-meta-value">★ {movie.get("vote_average", 0):.1f}/10</span></div>'
        
        # Add language information
        if movie.get('original_language'):
            language_code = movie.get('original_language', '')
            language_name = {
                'en': 'English',
                'hi': 'Hindi',
                'es': 'Spanish',
                'fr': 'French',
                'de': 'German',
                'ja': 'Japanese',
                'ko': 'Korean',
                'zh': 'Chinese',
                'ru': 'Russian',
                'it': 'Italian'
            }.get(language_code, language_code.upper())
            
            meta_html += f'<div class="movie-meta-item"><span class="movie-meta-label">Language:</span> <span class="movie-meta-value">{language_name}</span></div>'
            
        meta_html += '</div>'
        st.markdown(meta_html, unsafe_allow_html=True)
        
        # Genres with improved styling
        if movie.get('genres'):
            genres_display = ", ".join(movie.get('genres', []))
            st.markdown(f'<div class="movie-genre"><span class="movie-meta-label">Genres:</span> {genres_display}</div>', unsafe_allow_html=True)
        
        # Production companies if available
        if movie.get('production_companies'):
            companies = ", ".join(movie.get('production_companies', []))
            st.markdown(f'<div class="movie-production"><span class="movie-meta-label">Production:</span> {companies}</div>', unsafe_allow_html=True)
        
        # Overview with better heading
        if movie.get('overview'):
            st.markdown('<h4>Synopsis</h4>', unsafe_allow_html=True)
            st.markdown(f'<div class="movie-overview">{movie.get("overview", "No overview available.")}</div>', unsafe_allow_html=True)
        
        # Cast and crew with better formatting
        if movie.get('cast'):
            st.markdown('<h4>Cast & Crew</h4>', unsafe_allow_html=True)
            cast_html = '<div class="movie-cast">'
            cast_names = [f"<span class='cast-name'>{actor['name']}</span> as <span class='character-name'>{actor['character']}</span>" for actor in movie.get('cast', [])]
            cast_html += " | ".join(cast_names)
            cast_html += '</div>'
            st.markdown(cast_html, unsafe_allow_html=True)
        
        if movie.get('director'):
            st.markdown(f'<div class="movie-meta-item"><span class="movie-meta-label">Director:</span> <span class="movie-meta-value">{movie.get("director", "Unknown")}</span></div>', unsafe_allow_html=True)
    
    # Add CSS for the new elements
    st.markdown("""
    <style>
    .where-to-watch {
        background-color: rgba(20, 20, 20, 0.7);
        padding: 15px;
        border-radius: 8px;
        margin-top: 15px;
    }
    .where-to-watch h4 {
        color: #E50914;
        margin-bottom: 10px;
    }
    .streaming-services {
        list-style-type: none;
        padding: 0;
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .streaming-services li {
        margin-bottom: 8px;
    }
    .streaming-services a {
        color: #ffffff;
        text-decoration: none;
        display: block;
        padding: 5px 10px;
        background-color: rgba(40, 40, 40, 0.7);
        border-radius: 4px;
        transition: background-color 0.3s;
    }
    .streaming-services a:hover {
        background-color: rgba(229, 9, 20, 0.7);
    }
    .provider-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        background-color: rgba(40, 40, 40, 0.7);
        border-radius: 8px;
        padding: 8px;
        width: 80px;
        text-align: center;
        transition: transform 0.3s, background-color 0.3s;
    }
    .provider-item:hover {
        transform: scale(1.05);
        background-color: rgba(60, 60, 60, 0.7);
    }
    .provider-logo {
        width: 50px;
        height: 50px;
        border-radius: 8px;
        margin-bottom: 5px;
    }
    .provider-name {
        font-size: 0.8em;
        line-height: 1.2;
    }
    .streaming-note {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 10px;
    }
    .cast-name {
        color: #E50914;
        font-weight: bold;
    }
    .character-name {
        font-style: italic;
    }
    .movie-tagline {
        font-style: italic;
        color: #cccccc;
        margin: 15px 0;
        font-size: 1.1em;
        text-align: center;
    }
    .content-rating {
        margin-top: 10px;
        text-align: center;
    }
    .rating-badge {
        background-color: #E50914;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .awards-section {
        background-color: rgba(20, 20, 20, 0.7);
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .awards-section h4 {
        color: #E50914;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Award information (placeholder since actual data isn't available)
    st.markdown('<div class="awards-section"><h4>Awards & Recognition</h4><p>Information about awards and nominations would appear here if available from the API.</p></div>', unsafe_allow_html=True)
    
    # Trailer section with improved styling
    if movie.get('trailer'):
        st.subheader("Watch Trailer")
        trailer_url = f"https://www.youtube.com/embed/{movie.get('trailer')}"
        st.markdown(f'<iframe width="100%" height="400" src="{trailer_url}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>', unsafe_allow_html=True)
    
    # User rating section
    st.subheader("Rate this movie")
    
    user_rating = st.slider("Your rating", 1, 10, 8)
    
    from quiz import get_or_create_user
    import database as db
    
    if st.button("Submit Rating", key=f"rate_btn_{movie.get('id')}"):
        user_id = get_or_create_user()
        if user_id:
            # Save rating to database
            if db.save_user_rating(user_id, movie, user_rating):
                st.success(f"Thanks for rating this movie {user_rating}/10!")
            else:
                st.error("Failed to save your rating. Please try again.")
        else:
            st.error("Unable to identify user. Please refresh and try again.")
