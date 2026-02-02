from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from spotify_manager import SpotifyManager
from history_manager import HistoryManager
from config import Config
import webbrowser
import threading
import time
import os

from spotipy.oauth2 import SpotifyOAuth
import spotipy

app = Flask(__name__)
# Load Config
app.config.from_object(Config)

# Initialize Session Interface
from flask_session import Session
Session(app)

# --- OAUTH SETUP ---
def create_spotify_oauth():
    """
    Crea el objeto OAuth leyendo de la configuración de la app.
    Devuelve None si faltan variables críticas.
    """
    client_id = app.config['SPOTIPY_CLIENT_ID']
    client_secret = app.config['SPOTIPY_CLIENT_SECRET']
    redirect_uri = app.config['SPOTIPY_REDIRECT_URI']

    # Debug Printing
    if not client_id: print("DEBUG ERROR: Missing SPOTIPY_CLIENT_ID")
    if not client_secret: print("DEBUG ERROR: Missing SPOTIPY_CLIENT_SECRET")
    if not redirect_uri: print("DEBUG ERROR: Missing SPOTIPY_REDIRECT_URI")

    # Check for placeholders
    if client_id == "your_client_id_here" or client_secret == "your_client_secret_here":
        print("CRITICAL ERROR: You have not updated the .env file with your real Spotify Credentials!")
        return None

    if not client_id or not client_secret or not redirect_uri:
        return None

    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative user-library-read user-read-private user-top-read user-modify-playback-state user-read-playback-state"
    )

history_mgr = HistoryManager()

def get_sp_manager():
    """
    Helper to get an authenticated SpotifyManager using Token from Session ONLY.
    """
    token_info = session.get('token_info')
    
    if not token_info:
        return None
    
    # Check if token is expired and refresh if needed
    sp_oauth = create_spotify_oauth()
    if sp_oauth and sp_oauth.is_token_expired(token_info):
        try:
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
        except Exception as e:
            print(f"CRITICAL: Error refreshing token in get_sp_manager: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return None

    sp = SpotifyManager()
    try:
        sp.authenticate_with_token(token_info)
        return sp
    except: 
        return None

# --- DECORATORS ---
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        sp = get_sp_manager()
        if not sp:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                 return jsonify({'success': False, 'error': 'Sesión caducada o no iniciada'}), 401
            flash("Sesión caducada. Por favor conecta con Spotify de nuevo.", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- ERROR HANDLING ---

@app.errorhandler(spotipy.exceptions.SpotifyException)
def handle_spotify_exception(e):
    if e.http_status == 401:
        flash("Tu sesión de Spotify ha caducado. Por favor, vuelve a conectar.", "info")
        session.clear() 
        return redirect(url_for('home'))
    return f"Error de Spotify: {e}", e.http_status

# --- ROUTES ---

@app.route('/login')
def login():
    sp_oauth = create_spotify_oauth()
    if sp_oauth:
        auth_url = sp_oauth.get_authorize_url()
        return redirect(auth_url)
    else:
        # Diagnose exactly what is missing
        missing = []
        if not app.config.get('SPOTIPY_CLIENT_ID'): missing.append('SPOTIPY_CLIENT_ID')
        if not app.config.get('SPOTIPY_CLIENT_SECRET'): missing.append('SPOTIPY_CLIENT_SECRET')
        if not app.config.get('SPOTIPY_REDIRECT_URI'): missing.append('SPOTIPY_REDIRECT_URI')
        
        return f"<h1>Error de Configuración</h1><p>El servidor no puede iniciar OAuth porque faltan las siguientes variables:</p><ul><li>{'</li><li>'.join(missing)}</li></ul><p>Por favor edita el archivo <code>.env</code> y reinicia el servidor.</p>", 500

@app.route('/callback')
def callback():
    sp_oauth = create_spotify_oauth()
    if not sp_oauth:
        return redirect(url_for('home'))

    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f"Error de autorización: {error}", "error")
        return redirect(url_for('home'))

    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info
        session['visual_login_success'] = True # Flag for frontend animation if needed
        return redirect(url_for('home'))
    except Exception as e:
        flash(f"Error de login: {e}", "error")
        return redirect(url_for('home'))

@app.route('/offline')
def offline():
    return render_template('offline.html')

@app.route('/', methods=['GET'])
def home():
    # If authenticated, show create.html with full features
    if session.get('token_info'):
        return render_template('create.html', page='create', is_authenticated=True, scrollable=False)
    
    # If NOT authenticated, show create.html with Login Button
    return render_template('create.html', page='create', is_authenticated=False, scrollable=False)

@app.route('/my-playlists')
@login_required
def my_playlists():
    sp = get_sp_manager()

    playlists = []
    current_user_id = None
    
    try:
        user = sp.sp.current_user()
        playlists = sp.get_user_playlists()
        current_user_id = user['id']
            
    except spotipy.exceptions.SpotifyException as e:
        if e.http_status == 401:
            raise e
        flash(f"Error de Spotify: {e}", "error")
    except Exception as e:
        print(f"DEBUG ERROR: {e}")
        flash(f"Error conectando con Spotify: {e}", "error")
    
    return render_template('playlists.html', page='playlists', playlists=playlists, current_user_id=current_user_id)

@app.route('/delete-playlist', methods=['POST'])
@login_required
def delete_playlist_route():
    playlist_id = request.form.get('playlist_id')
    sp = get_sp_manager()

    try:
        sp.delete_playlist(playlist_id)
        flash("checkmark", "visual_success")
    except Exception as e:
        flash(f"Error eliminando playlist: {e}", "error")
        
    return redirect(url_for('my_playlists'))

@app.route('/play', methods=['POST'])
def play_track():
    uri = request.json.get('uri')
    sp = get_sp_manager()
    if not sp:
        return jsonify({'success': False, 'error': 'No autenticado'}), 401

    try:
        sp.play_track(uri)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/history/delete', methods=['POST'])
def delete_from_history():
    playlist_id = request.form.get('playlist_id')
    playlist_url = request.form.get('playlist_url')
    sp = get_sp_manager()
    if not sp:
        flash("No autenticado.", "error")
        return redirect(url_for('home'))

    try:

        sp.delete_playlist(playlist_id)
        
        # 2. Remove from Local History
        history_mgr.remove_entry(playlist_url)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
        flash("Playlist eliminada de Spotify y del historial.", "success")
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f"Error eliminando: {e}", "error")
        
    return redirect(url_for('history'))


# REMOVED FOR COMPLIANCE: Audio proxy endpoint
# Proxying third-party audio may violate content redistribution policies
# Preview URLs are already public and can be played directly via HTML5 audio
"""
@app.route('/proxy/audio')
def proxy_audio():
    import requests
    from flask import Response
    url = request.args.get('url')
    if not url: return "Missing URL", 400
    try:
        # Professional-grade headers to avoid throttling
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'audio/mpeg, audio/*;q=0.9, */*;q=0.8',
            'Referer': 'https://www.deezer.com/'
        }
        resp = requests.get(url, headers=headers, timeout=10, stream=True)
        return Response(resp.content, content_type=resp.headers.get('Content-Type'))
    except Exception as e:
        return str(e), 500
"""

@app.route('/history', methods=['GET'])
def history():
    data = history_mgr.get_history()
    return render_template('history.html', page='history', history=data)

@app.route('/playlist/<playlist_id>/edit')
@login_required
def playlist_edit(playlist_id):
    sp = get_sp_manager()
    try:
        # Get tracks
        tracks = sp.get_playlist_tracks(playlist_id)
        playlist_info = sp.sp.playlist(playlist_id)
        
        results = []
        # Prepare IDs for bulk feature fetch
        track_ids = [t['id'] for t in tracks if t.get('id')]
        # NOTE: Spotify Audio Features API is blocked (403). 
        # BPM/Key will be fetched via Deezer in frontend or manual edit.
        features = {} 

        for t in tracks:
            # Default values since we can't bulk-fetch features anymore
            bpm = 0
            key_name = "?"

            # Construct a match object that matches review.html expectation
            track_obj = {
                'id': t['id'],
                'uri': t['uri'],
                'name': t['name'],
                'artist': t['artist'], 
                'album': t['album'],
                'image': t['image'], 
                'bpm': bpm,
                'key': key_name,
                'preview_url': t['preview_url'],
                'external_urls': {'spotify': f"https://open.spotify.com/track/{t['id']}"},
                'artist_ids': []
            }
            results.append(track_obj) # Temporarily store to enrich


        # Deezer BPM Enrichment for missing tracks
        missing_bpm_tracks = [tr for tr in results if tr.get('bpm', 0) == 0]
        if missing_bpm_tracks:
            from concurrent.futures import ThreadPoolExecutor
            def _repair(tr):
                b = sp._fetch_deezer_bpm(tr['artist'], tr['name'])
                if b > 0: tr['bpm'] = b
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(_repair, missing_bpm_tracks)



        # Final Formatting for review.html
        formatted_results = []
        for tr in results:
            formatted_results.append({
                'query': f"{tr['name']} - {tr['artist']}",
                'matches': [tr] 
            })
            
        # Set session state for editing
        session['editing_playlist_id'] = playlist_id
        session['playlist_name'] = playlist_info['name']
        session['editing_mode'] = True
        
        # Render review.html with pre-filled results
        return render_template('review.html', page='create', results=results, scrollable=True, editing=True)
        
    except Exception as e:
        flash(f"Error cargando editor: {e}", "error")
        return redirect(url_for('history'))

@app.route('/playlist/<playlist_id>', methods=['GET'])
@login_required
def playlist_detail(playlist_id):
    sp = get_sp_manager()

    # Get tracks
    tracks = sp.get_playlist_tracks(playlist_id)
    
    # NOTE: Spotify Audio Features API is blocked (403). 
    # Vibe calculation is disabled. Tracks will be enriched via frontend analyzer/Deezer.
    if tracks:
        # Initialize running totals for vibe calculation
        total_energy = 0
        total_dance = 0
        total_valence = 0
        total_bpm = 0
        count_features = 0

        for t in tracks:
            # Default values (Client-side analyzer will enrich these)
            t['key_name'] = "?"
            t['bpm'] = 0 
            t['energy_val'] = 0
            
            # If we had feature data (we don't right now server-side), we would sum it here
            # For now, these are 0
        
        # Default Vibe (Neutral baseline)
        vibe = {
            'energy': 50,
            'danceability': 50,
            'valence': 50,
            'bpm': 0
        }
        
        # Deezer BPM Enrichment for missing tracks
        missing_bpm_tracks = [t for t in tracks if t.get('bpm', 0) == 0]
        if missing_bpm_tracks:
            from concurrent.futures import ThreadPoolExecutor
            def _repair(t):
                b = sp._fetch_deezer_bpm(t['artist'], t['name'])
                if b > 0: t['bpm'] = b
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(_repair, missing_bpm_tracks)
            
            # Re-calculate vibe avg_bpm and pseudo-stats
            valid_bpms = [t['bpm'] for t in tracks if t.get('bpm', 0) > 0]
            if valid_bpms:
                avg_bpm = int(sum(valid_bpms) / len(valid_bpms))
                vibe['bpm'] = avg_bpm
                # Pseudo-logic: higher BPM usually correlates with higher energy
                vibe['energy'] = min(95, max(40, int(avg_bpm * 0.6)))
                # Pseudo-logic: danceability often peaks around 110-130 BPM
                vibe['danceability'] = min(90, max(45, 100 - abs(120 - avg_bpm)))
                vibe['valence'] = (vibe['energy'] + vibe['danceability']) // 2



    # Get playlist info (for header)
    try:
        playlist_info = sp.sp.playlist(playlist_id)
        current_user_info = sp.sp.current_user()
        current_user_id = current_user_info['id']
        is_owner = (playlist_info['owner']['id'] == current_user_id)
        print(f"DEBUG: Playlist Owner: {playlist_info['owner']['id']}, Current User: {current_user_id}, IS_OWNER: {is_owner}")
    except Exception as e:
        print(f"DEBUG ERROR fetching info: {e}")
        playlist_info = {'name': 'Playlist', 'owner': {'display_name': 'Usuario'}, 'images': [], 'external_urls': {'spotify': '#'}}
        is_owner = True # Fallback to true if we hit a weird error to at least show tools

    search_results = session.pop('playlist_search_results', None) # Get flash-like results

    return render_template('playlist_detail.html', page='playlists', tracks=tracks, playlist_info=playlist_info, playlist_id=playlist_id, search_results=search_results, is_owner=is_owner, vibe=vibe)

@app.route('/playlist/new/search-ajax', methods=['POST'])
def new_playlist_search_ajax():
    query = request.form.get('query')
    sp = get_sp_manager()
    if not sp:
        return jsonify({'results': []})

    if query:
        # Search for this single query, return 10 results
        results = sp.search_tracks([query], limit=10)
        
        flat_results = []
        if results and results[0]['matches']:
            flat_results = results[0]['matches']
            # NOTE: Spotify Audio Features API blocked. 
            # We skip enrichment here and let the client-side analyzer handle it.
            for r in flat_results:
                r['bpm'] = 0
                r['key'] = "?"
            
        return jsonify({'results': flat_results})
    
    return jsonify({'results': []})

@app.route('/playlist/<playlist_id>/search-ajax', methods=['POST'])
def playlist_search_ajax(playlist_id):
    query = request.form.get('query')
    sp = get_sp_manager()
    if not sp:
        return jsonify({'results': []})

    if query:
        # Set to exactly 10 per user request
        results = sp.search_tracks([query], limit=10)
        
        flat_results = []
        if results and results[0]['matches']:
            flat_results = results[0]['matches']
            # NOTE: Spotify Audio Features API blocked.
            for r in flat_results:
                r['bpm'] = 0
                r['key'] = "?"
            
        return jsonify({'results': flat_results})
    
    return jsonify({'results': []})

@app.route('/playlist/<playlist_id>/add', methods=['POST'])
@login_required
def playlist_add_track(playlist_id):
    uri = request.form.get('uri')
    sp = get_sp_manager()

    try:
        sp.add_track_to_playlist(playlist_id, uri)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
        flash("Canción añadida.", "success")
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f"Error añadiendo canción: {e}", "error")
        
    return redirect(url_for('playlist_detail', playlist_id=playlist_id))

@app.route('/playlist/<playlist_id>/remove', methods=['POST'])
@login_required
def playlist_remove_track(playlist_id):
    uri = request.form.get('uri')
    sp = get_sp_manager()

    try:
        sp.remove_track_from_playlist(playlist_id, uri)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
            
        flash("Canción eliminada.", "success")
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': str(e)}), 400
        flash(f"Error eliminando canción: {e}", "error")
        
    return redirect(url_for('playlist_detail', playlist_id=playlist_id))


@app.route('/logout')
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for('home'))

@app.route('/playlist/<playlist_id>/save-cover', methods=['POST'])
@login_required
def save_playlist_cover(playlist_id):
    image_b64 = request.json.get('image') 
    
    if image_b64:
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        sp = get_sp_manager()

        try:
            success = sp.upload_playlist_cover(playlist_id, image_b64)
            return jsonify({'success': success})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'No image provided'}), 400

@app.route('/playlist/<playlist_id>/reorder', methods=['POST'])
@login_required
def playlist_reorder(playlist_id):
    uris = request.json.get('uris', [])
    
    if uris:
        sp = get_sp_manager()

        try:
            sp.reorder_playlist(playlist_id, uris)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify({'success': False, 'error': 'No uris provided'}), 400

@app.route('/playlist/<playlist_id>/recommend', methods=['GET'])
@login_required
def playlist_recommendations(playlist_id):
    sp = get_sp_manager()
        
    try:
        tracks = sp.get_playlist_tracks(playlist_id)
        if not tracks:
            return jsonify({'results': []})
            
        seed_ids = [t['id'] for t in tracks[:5]] # Max 5 seeds
        recs = sp.get_recommendations(seed_ids, limit=12)
        return jsonify({'results': recs})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/analyze-live', methods=['POST'])
def analyze_live():
    songs_raw = request.form.get('songs', '')
    # Limit input to prevent DDoS/Timeouts
    song_list = [s.strip() for s in songs_raw.split('\n') if s.strip()]
    if len(song_list) > 50:
        song_list = song_list[:50]
        # Optionally warn? For live analysis, silent truncation is usually fine UX.

    sp_manager = get_sp_manager()
    if not song_list or not sp_manager:
        return jsonify({'success': False})

    try:
        
        # Take a sample for live analysis (first 6 songs to be fast)
        sample = song_list[:6]
        search_results = sp_manager.search_tracks(sample, limit=1)
        
        track_ids = []
        actual_artist_ids = []
        for res in search_results:
            if res['matches']:
                match = res['matches'][0]
                track_ids.append(match['id'])
                actual_artist_ids.extend(match['artist_ids'])

        if not track_ids:
            return jsonify({'success': False})

        # NOTE: Spotify Audio Features API is blocked.
        # Smart Analyze "Vibe" stats are disabled.
        avg_energy = 0
        avg_val = 0
        avg_dance = 0
            
        # Simple Emotion Mapping
        emotion = "Neutral"
        if avg_val > 0.6 and avg_energy > 0.6: emotion = "Euphoric / Happy"
        elif avg_val > 0.6: emotion = "Chill / Positive"
        elif avg_val < 0.4 and avg_energy > 0.6: emotion = "Dark / Intense"
        elif avg_val < 0.4: emotion = "Sad / Melancholic"

        # Top Genres
        from collections import Counter
        top_genres = [g for g, c in Counter(genres).most_common(3)]

        return jsonify({
            'success': True,
            'energy': int(avg_energy * 100),
            'valence': int(avg_val * 100),
            'dance': int(avg_dance * 100),
            'emotion': emotion,
            'genres': top_genres
        })
            
    except Exception as e:
        print(f"Live Analysis Error: {e}")
        
    return jsonify({'success': False})

@app.route('/recommend-from-ids', methods=['POST'])
@login_required
def recommend_from_ids():
    track_ids = request.json.get('track_ids', [])
    if not track_ids:
        return jsonify({'results': []})
        
    sp = get_sp_manager()
    try:
        # Use first 5 as seeds
        recs = sp.get_recommendations(track_ids[:5], limit=12)
        return jsonify({'results': recs})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/search', methods=['GET', 'POST'])
def search_phase():
    if request.method == 'GET':
        return redirect(url_for('home'))
        
    # Update from form if provided
    playlist_name = request.form.get('playlist_name')
    songs_raw = request.form.get('songs')

    session['playlist_name'] = playlist_name
    session['songs_raw'] = songs_raw

    session['songs_raw'] = songs_raw

    sp_manager = get_sp_manager()
    if not sp_manager:
        flash("Por favor conecta tus credenciales o inicia sesión con Spotify.", "error")
        return redirect(url_for('home'))

    try:
        # User is already authenticated via manager
        user = sp_manager.sp.current_user()

        # Clean inputs: Remove leading numbers/dots/checkmarks (e.g. "1. Song", "- Song", "*) Song")
        import re
        song_list = []
        for s in songs_raw.split('\n'):
            cleaned = s.strip()
            # Remove leading numbers, dots, dashes, parentheses
            cleaned = re.sub(r'^[\d\.\-\)\s]+', '', cleaned)
            if cleaned:
                song_list.append(cleaned)
        if not song_list:
            flash("Lista vacía.", "error")
            return redirect(url_for('home'))
        # 3. Buscar en Spotify
        # UPDATED: Limit set to exactly 10 as requested
        results = sp_manager.search_tracks(song_list, limit=10)


        # BPM ENRICHMENT: Using Deezer API
        # Note: Spotify Audio Features API is restricted to approved apps (returns 403)
        # We use Deezer as primary BPM source with local analyzer as fallback
        all_ids = []
        for res in results:
            for match in res['matches']:
                all_ids.append(match['id'])
                match['bpm'] = 0  # Initialize
                match['key'] = "?"
        
        if all_ids:
            print(f"DEBUG: Processing {len(all_ids)} tracks for BPM via Deezer...")
            
            # Deezer BPM Enrichment
            missing_bpm_matches = []
            for res in results:
                for match in res['matches']:
                    if not match.get('bpm') or match['bpm'] == 0:
                        missing_bpm_matches.append(match)
            
            if missing_bpm_matches:
                from concurrent.futures import ThreadPoolExecutor
                def _fetch_bpm_fallback(match):
                    bpm = sp_manager._fetch_deezer_bpm(match['artist'], match['name'])
                    if bpm > 0:
                        match['bpm'] = bpm
                
                with ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(_fetch_bpm_fallback, missing_bpm_matches)
                
                final_bpm_count = sum(1 for res in results for m in res['matches'] if m.get('bpm', 0) > 0)
                print(f"DEBUG: Enriched {final_bpm_count} tracks with BPM from Deezer")



        return render_template('review.html', page='create', results=results, scrollable=True)

    except Exception as e:
        flash(f"Error: {str(e)}", "error")
        return redirect(url_for('home'))

@app.route('/create', methods=['POST'])
@login_required
def create_phase():
    sp_manager = get_sp_manager()

    try:
        selected_uris = []
        form_data = request.form
        
        # 1. HONOR MODAL ORDER (if available)
        if form_data.get('use_ordered_list') == 'true':
            selected_uris = request.form.getlist('final_uris')
        else:
            # Fallback to standard checkbox loop
            for key, value in form_data.items():
                if key.startswith("track_") and value != "SKIP":
                    selected_uris.append(value)

        if not selected_uris:
            flash("No seleccionaste ninguna canción válida.", "error")
            return redirect(url_for('home'))

        # Prioritize form data (editable title in review.html) over session data from previous step
        playlist_name = request.form.get('playlist_name') or session.get('playlist_name') or "Mi Playlist Generada"

        # CHECK FOR EDIT MODE
        editing_id = session.get('editing_playlist_id')
        
        if editing_id:
            # UPDATE EXISTING PLAYLIST
            sp_manager.reorder_playlist(editing_id, selected_uris)
            sp_manager.update_playlist_details(editing_id, name=playlist_name)
            
            # Sync local history
            result_url = f"https://open.spotify.com/playlist/{editing_id}"
            history_mgr.update_entry(result_url, name=playlist_name, count=len(selected_uris))
            
            # Clear Edit Mode
            session.pop('editing_playlist_id', None)
            session.pop('editing_mode', None)
            
            result_url = f"https://open.spotify.com/playlist/{editing_id}"
            flash(f"Playlist actualizada con éxito. <a href='{result_url}' target='_blank' class='underline'>Ver en Spotify</a>", "success")
            return redirect(url_for('history'))
            
        else:
            # CREATE NEW PLAYLIST
            result = sp_manager.create_playlist_with_tracks(playlist_name, selected_uris)
            
            # Save to History
            history_mgr.add_entry(playlist_name, result['playlist_url'], result['total_added'])
            
            # Upload Custom Cover if present (Only for new playlists for now, or add support for edit)
            cover_b64 = form_data.get('cover_image')
            if cover_b64:
                if "," in cover_b64:
                    cover_b64 = cover_b64.split(",")[1]
                try:
                    sp_manager.upload_playlist_cover(result['playlist_id'], cover_b64)
                except Exception as e:
                    print(f"Cover upload failed: {e}") 

            link = result['playlist_url']
            flash(f"Playlist creada con éxito ({result['total_added']} tracks). <a href='{link}' target='_blank' class='underline'>Abrir</a>", "success")
            
            return redirect(url_for('history'))

    except Exception as e:
        flash(f"Error creando playlist: {e}", "error")
        return redirect(url_for('home'))

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # threading.Thread(target=open_browser).start() # Disable auto-open to prevent confusion
    print(f"Iniciando servidor en http://0.0.0.0:5500 (Debug: {app.config['DEBUG']})")
    app.run(host='0.0.0.0', port=5500, debug=app.config['DEBUG'], use_reloader=app.config['DEBUG'])
