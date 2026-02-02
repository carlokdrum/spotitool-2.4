import requests
from spotify_manager import SpotifyManager

def debug_levitating():
    sm = SpotifyManager()
    artist = "Dua Lipa"
    track = "Levitating (feat. DaBaby)"
    clean = sm._clean_track_name(track)
    print(f"Original: {track} | Cleaned: {clean}")
    
    q = f"{artist} {clean}"
    url = f"https://api.deezer.com/search?q={q}"
    resp = requests.get(url).json()
    
    for item in resp.get('data', [])[:5]:
        track_id = item['id']
        detail = requests.get(f"https://api.deezer.com/track/{track_id}").json()
        print(f"ID: {track_id} | Title: {detail.get('title')} | BPM: {detail.get('bpm')}")

if __name__ == "__main__":
    debug_levitating()
