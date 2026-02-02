from spotify_manager import SpotifyManager
import os
from flask import Flask, session
from dotenv import load_dotenv

# Mocking flask setup to allow SpotifyManager to work if it depends on session?
# Actually SpotifyManager methods mostly depend on self.sp which is passed or init.
# But get_sp_manager in app.py handles the oauth. 

# Let's try to instantiate using client credentials if possible, or print instructions.
# Since we are in the user's environment, we can try to load the .env

load_dotenv()

def debug_api():
    print("--- Debugging Audio Features ---")
    client_id = os.environ.get('SPOTIPY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("Error: Creds not found in env.")
        return

    # Use Client Credentials Flow for testing (features are public usually)
    from spotipy.oauth2 import SpotifyClientCredentials
    import spotipy
    
    try:
        auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
        sp_client = spotipy.Spotify(auth_manager=auth_manager)
        
        # Search for the tracks
        queries = ["Blinding Lights The Weeknd", "Shape of You Ed Sheeran", "PAM Justin Quiles"]
        
        for q in queries:
            print(f"\nSearching for: {q}")
            res = sp_client.search(q, limit=1, type='track')
            if res['tracks']['items']:
                track = res['tracks']['items'][0]
                tid = track['id']
                print(f"Found: {track['name']} (ID: {tid})")
                
                # Get Features
                features = sp_client.audio_features([tid])
                if features and features[0]:
                    f = features[0]
                    print(f"API BPM: {f['tempo']}")
                    print(f"API Energy: {f['energy']}")
                    print(f"API Valence: {f['valence']}")
                else:
                    print("API returned NO features for this track.")
            else:
                print("Track not found.")
                
    except Exception as e:
        print(f"Crash: {e}")

if __name__ == "__main__":
    debug_api()
