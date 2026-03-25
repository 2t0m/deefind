from flask import Flask, request, jsonify, abort
import requests
import os
from dotenv import load_dotenv
import deezer
from deemix import generateDownloadObject
from deemix.downloader import Downloader
from deemix.settings import load as loadSettings
import re

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.')

STATIC_ASSETS = {'app.js', 'manifest.json', 'styles.css', 'sw.js'}

# Environment variables
DEEZER_ARL = os.environ.get('DEEZER_ARL', '')
NAVIDROME_URL = os.environ.get('NAVIDROME_URL', 'http://192.168.1.155:4533')
NAVIDROME_USER = os.environ.get('NAVIDROME_USER', 'admin')
NAVIDROME_PASS = os.environ.get('NAVIDROME_PASS', 'admin')
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/downloads')

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

# Initialize downloader
try:
    downloader = DeezerDownloader(DEEZER_ARL, DOWNLOAD_DIR)
    print(f"✅ Deezer downloader initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Deezer downloader: {str(e)}")
    downloader = None

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
            response = requests.get('https://api.deezer.com/chart/')
            data = response.json()
            # Return tracks from chart
            return jsonify({'data': data.get('tracks', {}).get('data', [])})
        else:
            # Search in Deezer API
            response = requests.get(f'https://api.deezer.com/search?q={query}')
            data = response.json()
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
            response = requests.get('https://api.deezer.com/chart/')
            data = response.json()
            return jsonify({'data': data.get('albums', {}).get('data', [])})
        else:
            # Search albums in Deezer API
            response = requests.get(f'https://api.deezer.com/search/album?q={query}')
            data = response.json()
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
            response = requests.get('https://api.deezer.com/chart/')
            data = response.json()
            return jsonify({'data': data.get('playlists', {}).get('data', [])})
        else:
            # Search playlists in Deezer API
            response = requests.get(f'https://api.deezer.com/search/playlist?q={query}')
            data = response.json()
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
    if not downloader:
        return jsonify({'error': 'Deezer downloader not initialized. Check DEEZER_ARL token.'}), 500
    
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
        result = downloader.download(link)
        print(f'✅ Download started: {result}')
        
        return jsonify(result)
    except Exception as e:
        print(f'❌ Download error: {str(e)}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1234)
