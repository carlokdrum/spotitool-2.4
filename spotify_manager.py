import spotipy
from spotipy.oauth2 import SpotifyOAuth

class SpotifyManager:
    KEY_MAP = {
        0: 'C', 1: 'C#', 2: 'D', 3: 'D#', 4: 'E', 5: 'F', 
        6: 'F#', 7: 'G', 8: 'G#', 9: 'A', 10: 'A#', 11: 'B'
    }

    def __init__(self):
        self.sp = None

    def authenticate_with_token(self, token_info):
        """
        Autentica usando un token OAuth existente (flujo web).
        Si el token ha expirado, intenta renovarlo automáticamente.
        """
        # Proactive Token Refresh check could happen here if we had the auth_manager
        # But commonly, the spotipy client handles refresh if initialized with auth_manager
        # Here we are initializing with a static token.
        
        # Validar expiración si es posible
        from spotipy import Spotify
        self.sp = Spotify(auth=token_info['access_token'], requests_timeout=10, retries=3)
        return self.sp.current_user()

    # Shared session for Deezer lookups to reuse SSL handshakes
    _deezer_session = None

    def _get_deezer_session(self):
        import requests
        if self._deezer_session is None:
            self._deezer_session = requests.Session()
            self._deezer_session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
            })
        return self._deezer_session

    def _clean_track_name(self, name):
        """Limpia el nombre de la canción para mejorar la búsqueda en Deezer"""
        import re
        # 1. Remover featurings y cualquier cosa entre paréntesis/corchetes que los contenga
        name = re.sub(r'[\(\[][^()\[\]]*(feat\.|ft\.|with|featuring)[^()\[\]]*[\)\]]', '', name, flags=re.IGNORECASE)
        # 2. Remover metadatos comunes entre paréntesis o corchetes que quedaron
        name = re.sub(r'[\(\[][^()\[\]]*(Official|Video|Remastered|Remix|Single|Version|Deluxe|Edit|Radio|Club|Original|Studio|Live|Bonus|Track|Mixed)[^()\[\]]*[\)\]]', '', name, flags=re.IGNORECASE)
        # 3. Remover extras después de guiones si parecen metadatos
        name = re.sub(r'\s-\s.*(Remastered|Remix|Mix|Version|Edit|Radio|Club|Live|Studio).*$', '', name, flags=re.IGNORECASE)
        # 4. Limpieza final: quitar feat. sueltos y caracteres raros
        name = re.sub(r'\s+(feat\.|ft\.|with)\s+.*$', '', name, flags=re.IGNORECASE)
        name = name.replace('"', '').replace("'", "").strip()
        # Eliminar puntuación final
        name = re.sub(r'[\-\s\(\)\[\]]+$', '', name)
        return name.strip()

    def _fetch_deezer_bpm(self, artist_name, track_name):
        """Helper para buscar BPM en Deezer con búsqueda ultra-agresiva"""
        try:
            session = self._get_deezer_session()
            clean_track = self._clean_track_name(track_name)
            
            # 1. Búsqueda combinada (Atista + Canción)
            dq = f"{artist_name} {clean_track}"
            url = f"https://api.deezer.com/search?q={dq}&limit=5"
            d_resp = session.get(url, timeout=3.0).json()
                
            if d_resp.get('data'):
                for item in d_resp['data']:
                    detail = session.get(f"https://api.deezer.com/track/{item['id']}", timeout=2.5).json()
                    bpm = detail.get('bpm', 0)
                    if bpm and bpm > 0: return int(float(bpm))

            # 2. Búsqueda desesperada: Solo canción (si la anterior falló)
            url_only_track = f"https://api.deezer.com/search?q={clean_track}&limit=10"
            d_resp_alt = session.get(url_only_track, timeout=3.0).json()
            if d_resp_alt.get('data'):
                for item in d_resp_alt['data']:
                    # Verificar si el artista coincide minimamente
                    if artist_name.lower() in item['artist']['name'].lower() or item['artist']['name'].lower() in artist_name.lower():
                        detail = session.get(f"https://api.deezer.com/track/{item['id']}", timeout=2.5).json()
                        bpm = detail.get('bpm', 0)
                        if bpm and bpm > 0: return int(float(bpm))
        except: pass
        return 0

    def _fetch_deezer_preview(self, artist_name, track_name):
        """Helper para buscar preview en Deezer si Spotify no lo tiene"""
        try:
            session = self._get_deezer_session()
            clean_track = self._clean_track_name(track_name)
            
            dq = f'artist:"{artist_name}" track:"{clean_track}"'
            d_resp = session.get(f"https://api.deezer.com/search?q={dq}&limit=1", timeout=2.0).json()
            
            if not d_resp.get('data'):
                dq_open = f"{artist_name} {clean_track}"
                d_resp = session.get(f"https://api.deezer.com/search?q={dq_open}&limit=1", timeout=2.0).json()
                
            if d_resp.get('data'):
                return d_resp['data'][0]['preview']
        except: pass
        return None

    def search_tracks(self, queries, limit=5, progress_callback=None):
        """
        Searches for a list of queries in parallel (Spotify + Deezer Fallback).
        """
        if not self.sp:
            raise Exception("No autenticado")

        results = [None] * len(queries)
        
        def _search_single(index, query):
            if progress_callback:
                progress_callback(f"Buscando: {query}...")

            try:
                clean_q = query.strip()
                if not clean_q: 
                    results[index] = {'query': query, 'matches': []}
                    return
                
                resp = self.sp.search(q=clean_q, limit=limit, type='track')
                
                matches = []
                for item in resp['tracks']['items']:
                    image = item['album']['images'][0]['url'] if item['album']['images'] else None
                    preview_url = item['preview_url']

                    # Fallback to Deezer
                    if not preview_url:
                        artist = item['artists'][0]['name']
                        preview_url = self._fetch_deezer_preview(artist, item['name'])

                    matches.append({
                        'id': item['id'],
                        'uri': item['uri'],
                        'name': item['name'],
                        'artist': ", ".join([a['name'] for a in item['artists']]),
                        'artist_ids': [a['id'] for a in item['artists']],
                        'image': image,
                        'preview_url': preview_url,
                        'external_url': item['external_urls']['spotify']
                    })
                
                results[index] = {'query': query, 'matches': matches}
            except Exception as e:
                print(f"Error searching for {query}: {e}")
                results[index] = {'query': query, 'matches': []}

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=20) as executor:
            for i, q in enumerate(queries):
                executor.submit(_search_single, i, q)
        
        return [r for r in results if r is not None]

    def create_playlist_with_tracks(self, playlist_name, track_uris):
        """
        Crea una playlist con una lista exacta de URIs.
        """
        if not self.sp:
            raise Exception("No autenticado")

        user_id = self.sp.current_user()['id']
        
        # 1. Crear playlist
        playlist = self.sp.user_playlist_create(user_id, playlist_name)
        
        # 2. Añadir canciones (lotes de 100)
        track_uris = [u for u in track_uris if u] # Filtrar vacíos
        
        if track_uris:
            for i in range(0, len(track_uris), 100):
                self.sp.playlist_add_items(playlist['id'], track_uris[i:i+100])
        
        return {
            'playlist_url': playlist['external_urls']['spotify'],
            'playlist_id': playlist['id'],
            'total_added': len(track_uris)
        }

    def get_user_playlists(self):
        """Obtiene TODAS las playlists del usuario (sin límite)"""
        if not self.sp: return []
        try:
            playlists = []
            results = self.sp.current_user_playlists(limit=50)
            playlists.extend(results['items'])
            
            # Pagination loop
            while results['next']:
                results = self.sp.next(results)
                playlists.extend(results['items'])
                
            return playlists
        except Exception as e:
            print(f"Error fetching playlists: {e}")
            return []

    def get_playlist_tracks(self, playlist_id):
        """Obtiene las canciones de una playlist con Fallback de Audio Paralelo"""
        if not self.sp: return []
        try:
            # 1. Fetch from Spotify
            first_page = self.sp.playlist_items(playlist_id, limit=100, offset=0)
            total = first_page['total']
            all_items = first_page['items']
            
            if total > 100:
                offsets = range(100, total, 100)
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = executor.map(lambda o: self.sp.playlist_items(playlist_id, limit=100, offset=o)['items'], offsets)
                    for page_items in results: all_items.extend(page_items)
            
            # 2. Extract basic data
            tracks = []
            for item in all_items:
                if not item or not item.get('track'): continue
                t = item['track']
                img = t['album']['images'][0]['url'] if t['album'].get('images') else None
                tracks.append({
                    'id': t['id'], 'name': t['name'], 'artist': t['artists'][0]['name'],
                    'album': t['album']['name'], 'image': img, 'uri': t['uri'],
                    'preview_url': t['preview_url'] # Original from Spotify
                })

            # 3. Parallel Fallback for missing previews
            missing_indices = [i for i, t in enumerate(tracks) if not t['preview_url']]
            if missing_indices:
                from concurrent.futures import ThreadPoolExecutor
                def _repair(idx):
                    t = tracks[idx]
                    tracks[idx]['preview_url'] = self._fetch_deezer_preview(t['artist'], t['name'])

                with ThreadPoolExecutor(max_workers=10) as executor:
                    executor.map(_repair, missing_indices)
            
            return tracks
        except Exception as e:
            print(f"Error fetching tracks: {e}")
            return []

    def section_add_remove(self): pass # Marker

    def add_track_to_playlist(self, playlist_id, track_uri):
        """Añade una canción a la playlist"""
        if not self.sp: raise Exception("No autenticado")
        self.sp.playlist_add_items(playlist_id, [track_uri])

    def remove_track_from_playlist(self, playlist_id, track_uri):
        """Elimina una canción de la playlist"""
        if not self.sp: raise Exception("No autenticado")
        self.sp.playlist_remove_all_occurrences_of_items(playlist_id, [track_uri])

    def get_audio_features(self, track_ids):
        """Obtiene energía, bailabilidad, etc. para una lista de IDs"""
        if not self.sp or not track_ids: return {}
        try:
            # Spotify allows up to 100 IDs per request
            features_list = []
            for i in range(0, len(track_ids), 100):
                ids_batch = track_ids[i:i+100]
                batch = self.sp.audio_features(ids_batch)
                if batch:
                    features_list.extend(batch)
            
            # Map by ID
            results = {f['id']: f for f in features_list if f}
            return results
        except Exception as e:
            import traceback
            print(f"Error fetching audio features: {e}")
            print(f"Full traceback: {traceback.format_exc()}")
            return {}

    def delete_playlist(self, playlist_id):
        """Elimina (deja de seguir) una playlist"""
        if not self.sp: raise Exception("No autenticado")
        self.sp.current_user_unfollow_playlist(playlist_id)

    def reorder_playlist(self, playlist_id, track_uris):
        """Reemplaza completamente el orden de una playlist"""
        if not self.sp: raise Exception("No autenticado")
        
        # Spotify API: replace_playlist_items replaces ALL items
        # It's safer to use this for a full reorder than reorder_playlist_items in a loop
        self.sp.playlist_replace_items(playlist_id, track_uris)

    def update_playlist_details(self, playlist_id, name=None, description=None):
        """Actualiza metadatos de la playlist"""
        if not self.sp: raise Exception("No autenticado")
        data = {}
        if name: data['name'] = name
        if description: data['description'] = description
        
        if data:
            self.sp.playlist_change_details(playlist_id, **data)

    def get_recommendations(self, seed_track_ids, limit=10):
        """Obtiene recomendaciones basadas en tracks semilla"""
        if not self.sp or not seed_track_ids: return []
        try:
            # Max 5 seeds allowed by Spotify
            seeds = seed_track_ids[:5]
            results = self.sp.recommendations(seed_tracks=seeds, limit=limit)
            
            recs = []
            for track in results['tracks']:
                img = track['album']['images'][0]['url'] if track['album']['images'] else None
                recs.append({
                    'id': track['id'],
                    'uri': track['uri'],
                    'name': track['name'],
                    'artist': ", ".join([a['name'] for a in track['artists']]),
                    'image': img,
                    'preview_url': track['preview_url'],
                    'external_url': track['external_urls']['spotify']
                })
            return recs
        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []

    def upload_playlist_cover(self, playlist_id, image_b64):
        """Sube una imagen de portada (base64) a la playlist"""
        if not self.sp: raise Exception("No autenticado")
        try:
            self.sp.playlist_upload_cover_image(playlist_id, image_b64)
            return True
        except Exception as e:
            print(f"Error uploading cover: {e}")
            return False

    def play_track(self, uri):
        """Reproduce una canción en el dispositivo activo"""
        if not self.sp: raise Exception("No autenticado")
        
        devices = self.sp.devices()
        if not devices['devices']:
            raise Exception("No hay dispositivos activos. Abre Spotify en tu ordenador o móvil.")
            
        self.sp.start_playback(uris=[uri])
