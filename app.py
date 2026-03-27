from flask import Flask, request, jsonify, abort
from flask_compress import Compress
import requests
import os
from dotenv import load_dotenv
import deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader
from deemix.settings import load as loadSettings
import re
from time import time
from threading import Lock

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.')
app.config['COMPRESS_MIMETYPES'] = [
    'text/html',
    'text/css',
    'application/javascript',
    'application/json',
    'text/plain',
    'image/svg+xml'
]
app.config['COMPRESS_LEVEL'] = 5
app.config['COMPRESS_MIN_SIZE'] = 500
Compress(app)

STATIC_ASSETS = {'app.js', 'manifest.json', 'styles.css', 'sw.js'}

# Environment variables
DEEZER_ARL = os.environ.get('DEEZER_ARL', '')
NAVIDROME_URL = os.environ.get('NAVIDROME_URL', 'http://192.168.1.155:4533')
NAVIDROME_USER = os.environ.get('NAVIDROME_USER', 'admin')
NAVIDROME_PASS = os.environ.get('NAVIDROME_PASS', 'admin')
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/downloads')

http = requests.Session()
_api_cache = {}
_CACHE_TTL_DEFAULT = 30

downloader = None
downloader_error = None
downloader_lock = Lock()

class DownloadListener:
    """Simple listener for deemix downloads"""
    def send(self, key, value=None):
        """Handle download events"""
        if key == 'updateQueue':
            pass  # Queue updated
        elif key == 'startDownload':
            print(f"Starting download: {value}")
        elif key == 'finishDownload':
            print(f"Finished download: {value}")

class DeezerDownloader:
    """Handles direct downloads from Deezer using deemix"""
    
    def __init__(self, arl, download_dir):
        self.arl = arl
        self.download_dir = download_dir
        self.dz = deezer.Deezer()
        
        # Login with ARL
        if not self.dz.login_via_arl(arl):
            raise Exception("Invalid Deezer ARL token")
        
        # Load default settings
        self.settings = loadSettings()
        
        # Configure download settings
        self.settings['downloadLocation'] = download_dir
        self.settings['fallbackBitrate'] = True
        self.settings['createPlaylistFolder'] = True
        self.settings['tags']['savePlaylistAsCompilation'] = True
    
    def parse_deezer_url(self, url):
        """Parse Deezer URL to extract type and ID"""
        patterns = {
            'track': r'deezer\.com/(?:\w+/)?track/(\d+)',
            'album': r'deezer\.com/(?:\w+/)?album/(\d+)',
            'playlist': r'deezer\.com/(?:\w+/)?playlist/(\d+)',
        }
        
        for content_type, pattern in patterns.items():
            match = re.search(pattern, url)
            if match:
                return content_type, match.group(1)
        
        return None, None
    
    def download(self, url):
        """Download content from Deezer URL"""
        content_type, content_id = self.parse_deezer_url(url)
        
        if not content_type or not content_id:
            raise Exception("Invalid Deezer URL")
        
        try:
            # Generate download object
            download_obj = generateDownloadObject(self.dz, url, '128')  # Pass bitrate directly as string
            
            if not download_obj:
                raise Exception("Failed to generate download object")
            
            # Create listener
            listener = DownloadListener()
            
            # Create downloader instance with listener
            downloader = Downloader(self.dz, download_obj, self.settings, listener)
            
            # Start download
            downloader.start()
            
            return {
                'success': True,
                'type': content_type,
                'id': content_id,
                'message': f'{content_type.capitalize()} download started'
            }
        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

def get_downloader():
    """Lazy init to avoid slowing down app startup."""
    global downloader, downloader_error

    if downloader is not None:
        return downloader

    with downloader_lock:
        if downloader is not None:
            return downloader
        try:
            downloader = DeezerDownloader(DEEZER_ARL, DOWNLOAD_DIR)
            downloader_error = None
            print("✅ Deezer downloader initialized successfully")
        except Exception as e:
            downloader_error = str(e)
            print(f"❌ Failed to initialize Deezer downloader: {downloader_error}")
            downloader = None
    return downloader

def deezer_get_json(url, params=None, cache_ttl=_CACHE_TTL_DEFAULT):
    """Fetch Deezer JSON with timeout + short-lived cache for faster repeated queries."""
    params = params or {}
    cache_key = (url, tuple(sorted(params.items())))
    now = time()

    if cache_ttl > 0 and cache_key in _api_cache:
        cached_at, payload = _api_cache[cache_key]
        if now - cached_at < cache_ttl:
            return payload

    response = http.get(url, params=params, timeout=8)
    response.raise_for_status()
    payload = response.json()

    if cache_ttl > 0:
        _api_cache[cache_key] = (now, payload)
        if len(_api_cache) > 256:
            oldest_key = min(_api_cache, key=lambda k: _api_cache[k][0])
            del _api_cache[oldest_key]

    return payload

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/<path:filename>')
def static_assets(filename):
    if filename in STATIC_ASSETS:
        return app.send_static_file(filename)
    abort(404)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    try:
        if not query:
            # Load chart if search is empty
            data = deezer_get_json('https://api.deezer.com/chart/', cache_ttl=45)
            # Return tracks from chart
            return jsonify({'data': data.get('tracks', {}).get('data', [])[:24]})
        else:
            # Search in Deezer API
            data = deezer_get_json('https://api.deezer.com/search', params={'q': query, 'limit': 24}, cache_ttl=15)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_albums')
def search_albums():
    """Search for albums in Deezer"""
    query = request.args.get('q', '')
    
    try:
        if not query:
            # Load chart albums if search is empty
            data = deezer_get_json('https://api.deezer.com/chart/', cache_ttl=45)
            return jsonify({'data': data.get('albums', {}).get('data', [])[:24]})
        else:
            # Search albums in Deezer API
            data = deezer_get_json('https://api.deezer.com/search/album', params={'q': query, 'limit': 24}, cache_ttl=15)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_playlists')
def search_playlists():
    """Search for playlists in Deezer"""
    query = request.args.get('q', '')
    
    try:
        if not query:
            # Load chart playlists if search is empty
            data = deezer_get_json('https://api.deezer.com/chart/', cache_ttl=45)
            return jsonify({'data': data.get('playlists', {}).get('data', [])[:24]})
        else:
            # Search playlists in Deezer API
            data = deezer_get_json('https://api.deezer.com/search/playlist', params={'q': query, 'limit': 24}, cache_ttl=15)
            return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/album_tracks/<album_id>')
def album_tracks(album_id):
    """Get tracks from an album"""
    try:
        response = requests.get(f'https://api.deezer.com/album/{album_id}')
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/playlist_tracks/<playlist_id>')
def playlist_tracks(playlist_id):
    """Get tracks from a playlist"""
    try:
        response = requests.get(f'https://api.deezer.com/playlist/{playlist_id}')
        data = response.json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_navidrome_exists(artist, title):
    """Check if a song already exists in Navidrome"""
    try:
        # Search in Navidrome
        search_query = f'{artist} {title}'
        url = f'{NAVIDROME_URL}/rest/search3.view'
        params = {
            'u': NAVIDROME_USER,
            'p': NAVIDROME_PASS,
            'v': '1.16.1',
            'c': 'deefind',
            'f': 'json',
            'query': search_query
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'subsonic-response' in data:
                search_result = data['subsonic-response'].get('searchResult3', {})
                songs = search_result.get('song', [])
                
                # Check if any song matches artist and title
                for song in songs:
                    song_title = song.get('title', '').lower()
                    song_artist = song.get('artist', '').lower()
                    if artist.lower() in song_artist and title.lower() in song_title:
                        return True, song
        return False, None
    except Exception as e:
        print(f'⚠️ Navidrome check error: {str(e)}')
        return False, None

@app.route('/download', methods=['POST'])
def download():
    """Download music from Deezer"""
    active_downloader = get_downloader()
    if not active_downloader:
        error_msg = downloader_error or 'Deezer downloader not initialized. Check DEEZER_ARL token.'
        return jsonify({'error': error_msg}), 500
    
    data = request.get_json()
    link = data.get('link')
    title = data.get('title', '')
    artist = data.get('artist', '')
    
    if not link:
        return jsonify({'error': 'No link provided'}), 400
    
    # Check if song already exists in Navidrome (only for tracks)
    if 'track' in link and title and artist:
        exists, existing_song = check_navidrome_exists(artist, title)
        if exists:
            print(f'⚠️ Song already exists in Navidrome: {artist} - {title}')
            return jsonify({
                'success': False,
                'error': 'already_exists',
                'message': f'Already in library: {artist} - {title}'
            }), 409
    
    try:
        print(f'\n📥 Downloading from Deezer: {link}')
        result = active_downloader.download(link)
        print(f'✅ Download started: {result}')
        
        return jsonify(result)
    except Exception as e:
        print(f'❌ Download error: {str(e)}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1234)
