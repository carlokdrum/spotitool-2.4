import requests

def test_deezer_remix_strategy():
    artist = "Dua Lipa"
    track = "Levitating"
    
    # Try searching with "Remix" appended
    q = f"{artist} {track} Remix"
    url = f"https://api.deezer.com/search?q={q}&limit=10"
    
    print(f"Testing Deezer 'Remix' strategy for {artist} - {track}:")
    try:
        resp = requests.get(url).json()
        for item in resp.get('data', []):
            track_id = item['id']
            detail = requests.get(f"https://api.deezer.com/track/{track_id}").json()
            bpm = detail.get('bpm', 0)
            if bpm and bpm > 0:
                print(f"✅ Found BPM on Remix: {detail.get('title')} -> BPM: {bpm}")
                # For BPM purposes, the remix is often the same tempo as the original (or 2x)
                # but it's better than nothing.
            else:
                print(f"❌ No BPM on: {detail.get('title')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_deezer_remix_strategy()
