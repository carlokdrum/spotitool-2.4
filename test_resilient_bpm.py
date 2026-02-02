from spotify_manager import SpotifyManager

def test_resilient_bpm():
    sm = SpotifyManager()
    
    test_cases = [
        ("Ed Sheeran", "Shape of You (Official Video)"),
        ("Lana Del Rey", "Honeymoon - Remastered"),
        ("The Weeknd", "Blinding Lights [Single Version]"),
        ("Dua Lipa", "Levitating (feat. DaBaby)"),
    ]
    
    print("Testing Resilient Deezer BPM Fallback:")
    print("-" * 40)
    for artist, track in test_cases:
        bpm = sm._fetch_deezer_bpm(artist, track)
        clean = sm._clean_track_name(track)
        status = "FIXED ✅" if bpm > 0 else "FAILED ❌"
        print(f"[{status}] {artist} - {track} (Clean: {clean}) -> BPM: {bpm}")

if __name__ == "__main__":
    test_resilient_bpm()
