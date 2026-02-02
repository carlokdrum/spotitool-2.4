import requests

def test_deezer_isrc_bpm():
    isrc = "GBAHT1901299" # Levitating Dua Lipa
    url = f"https://api.deezer.com/track/isrc:{isrc}"
    
    print(f"Testing Deezer ISRC for {isrc}:")
    resp = requests.get(url).json()
    if 'id' in resp:
        print(f"Found Track: {resp.get('title')} - BPM: {resp.get('bpm')}")
    else:
        print(f"No result for ISRC {isrc} in Deezer")

    # Try another one
    isrc2 = "GBARL2000215" # Another Levitating Version
    url2 = f"https://api.deezer.com/track/isrc:{isrc2}"
    print(f"\nTesting Deezer ISRC for {isrc2}:")
    resp2 = requests.get(url2).json()
    if 'id' in resp2:
        print(f"Found Track: {resp2.get('title')} - BPM: {resp2.get('bpm')}")
    else:
        print(f"No result for ISRC {isrc2} in Deezer")

if __name__ == "__main__":
    test_deezer_isrc_bpm()
