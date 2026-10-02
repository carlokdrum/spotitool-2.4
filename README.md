# SpotiTool

Flask app to build and edit Spotify playlists (BPM/key enrichment via Deezer + a local analyzer).

## Run locally
1. `pip install -r requirements.txt`
2. `cp .env.example .env` and fill in your Spotify credentials.
3. Register the same `SPOTIPY_REDIRECT_URI` in the Spotify developer dashboard.
4. `python app.py` and open http://127.0.0.1:5500

Layout: `templates/` (Jinja pages), `static/` (js, img, manifest). See `DEPLOY_ON_RENDER.md` for deployment.
