import streamlit as st
import database as db
import time

def show_login_page():
    """Display login page for user authentication"""
    st.markdown("## User Login")
    
    # Input fields for login
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Login", use_container_width=True):
            if username and password:
                user_id, auth_token = db.authenticate_user(username, password)
                
                if user_id and auth_token:
                    # Store authentication in session state
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.auth_token = auth_token
                    st.session_state.is_authenticated = True
                    
                    st.success("Login successful! Redirecting...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.warning("Please enter both username and password")
    
    with col2:
        if st.button("Register", use_container_width=True):
            # Switch to register view
            st.session_state.show_register = True
            st.rerun()

def show_register_page():
    """Display registration page for new users"""
    st.markdown("## Create Account")
    
    # Input fields for registration
    username = st.text_input("Username (3-20 characters)")
    email = st.text_input("Email (optional)")
    password = st.text_input("Password (min 6 characters)", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Register", use_container_width=True):
            # Validate inputs
            if len(username) < 3 or len(username) > 20:
                st.error("Username must be between 3 and 20 characters")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                # Create user account
                user_id, error = db.create_user_account(username, password, email)
                
                if user_id:
                    st.success("Account created successfully! Please login.")
                    
                    # Switch back to login view
                    st.session_state.show_register = False
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Failed to create account: {error}")
    
    with col2:
        if st.button("Back to Login", use_container_width=True):
            # Switch back to login view
            st.session_state.show_register = False
            st.rerun()

def show_logout_button():
    """Show logout button in the sidebar"""
    if st.session_state.get('is_authenticated', False):
        if st.sidebar.button("Logout"):
            # Clear authentication
            st.session_state.is_authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.auth_token = None
            st.rerun()
        
        st.sidebar.write(f"Logged in as: **{st.session_state.username}**")

def init_auth_state():
    """Initialize authentication state variables"""
    if 'is_authenticated' not in st.session_state:
        st.session_state.is_authenticated = False
    
    if 'show_register' not in st.session_state:
        st.session_state.show_register = False
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None

def authenticate():
    """Main authentication function to handle login flow"""
    # Initialize authentication state
    init_auth_state()
    
    # Initialize database tables
    db.create_user_tables()
    
    # Show logout button in sidebar
    show_logout_button()
    
    # If not authenticated, show login or register page
    if not st.session_state.is_authenticated:
        if st.session_state.show_register:
            show_register_page()
        else:
            show_login_page()
        
        return False
    
    return True