import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

load_dotenv()

def check_spotify_isrc():
    client_id = os.environ.get('SPOTIPY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIPY_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("Missing credentials")
        return

    sp = Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
    
    query = "Levitating Dua Lipa"
    results = sp.search(q=query, limit=1, type='track')
    
    if results['tracks']['items']:
        track = results['tracks']['items'][0]
        print(f"Track: {track['name']} by {track['artists'][0]['name']}")
        print(f"External IDs: {track.get('external_ids')}")
        if 'isrc' in track.get('external_ids', {}):
            print(f"ISRC found: {track['external_ids']['isrc']}")
        else:
            print("ISRC NOT found in search result")
    else:
        print("No results found")

if __name__ == "__main__":
    check_spotify_isrc()
