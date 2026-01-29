from flask import Flask, request, jsonify, send_from_directory
import requests
import os
from urllib.parse import quote
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='.')

# Environment variables
DOWNLOADER_API_URL = os.environ.get('DOWNLOADER_API_URL', 'http://192.168.1.155:5005')
NAVIDROME_URL = os.environ.get('NAVIDROME_URL', 'http://192.168.1.155:4533')
NAVIDROME_USER = os.environ.get('NAVIDROME_USER', 'admin')
NAVIDROME_PASS = os.environ.get('NAVIDROME_PASS', 'admin')

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/manifest.json')
def manifest():
    return app.send_static_file('manifest.json')

@app.route('/sw.js')
def service_worker():
    return app.send_static_file('sw.js')

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

@app.route('/send_to_downloader', methods=['POST'])
def send_to_downloader():
    data = request.get_json()
    link = data.get('link')
    title = data.get('title', '')
    artist = data.get('artist', '')
    
    if not link:
        return jsonify({'error': 'No link provided'}), 400
    
    # Check if song already exists in Navidrome
    if title and artist:
        exists, existing_song = check_navidrome_exists(artist, title)
        if exists:
            print(f'⚠️ Song already exists in Navidrome: {artist} - {title}')
            return jsonify({
                'success': False,
                'error': 'already_exists',
                'message': f'Already in library: {artist} - {title}'
            }), 409
    
    try:
        # Send to remote downloader server
        payload = {'link': link}
        api_url = f'{DOWNLOADER_API_URL}/api/download_from_link'
        print(f'\n📤 SENDING to {api_url}')
        print(f'   Payload: {payload}')
        
        response = requests.post(
            api_url,
            json=payload,
            timeout=5
        )
        
        print(f'📥 RESPONSE received:')
        print(f'   Status: {response.status_code}')
        print(f'   Response: {response.text}')
        print(f'   Headers: {dict(response.headers)}\n')
        
        return jsonify({'success': True, 'response': response.text})
    except Exception as e:
        print(f'❌ ERROR: {str(e)}\n')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1234)
