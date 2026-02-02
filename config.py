import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    # Security: Fail if SECRET_KEY is missing in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if os.environ.get('FLASK_ENV') == 'production':
            raise ValueError("No SECRET_KEY set for production configuration")
        SECRET_KEY = 'dev-default-secret-key-do-not-use-in-prod'

    # Session Config
    SESSION_TYPE = 'filesystem'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # Secure cookies only if we are in production or behind HTTPS
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    # Spotify Credentials
    SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
    SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
    SPOTIPY_REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI')

    # Debug toggle
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DEBUG = False

class DevelopmentConfig(Config):
    FLASK_ENV = 'development'
    DEBUG = True
