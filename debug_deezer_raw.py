import requests

def debug_deezer():
    q = "The Weeknd Blinding Lights"
    url = f"https://api.deezer.com/search?q={q}&limit=5"
    resp = requests.get(url).json()
    
    for item in resp.get('data', []):
        track_id = item['id']
        detail = requests.get(f"https://api.deezer.com/track/{track_id}").json()
        print(f"ID: {track_id} | Title: {detail.get('title')} | BPM: {detail.get('bpm')}")

if __name__ == "__main__":
    debug_deezer()
