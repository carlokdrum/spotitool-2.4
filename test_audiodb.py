import requests

def test_audiodb_bpm():
    artist = "Dua Lipa"
    track = "Levitating"
    # Public test key is '2'
    url = f"https://www.theaudiodb.com/api/v1/json/2/searchtrack.php?s={artist}&t={track}"
    
    print(f"Testing AudioDB for {artist} - {track}:")
    try:
        resp = requests.get(url).json()
        if resp.get('track'):
            t = resp['track'][0]
            print(f"Found: {t.get('strTrack')} - BPM: {t.get('intBPM')}")
            # print(t) # Debug all fields
        else:
            print("No result found in AudioDB")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_audiodb_bpm()
