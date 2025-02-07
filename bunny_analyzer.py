from flask import Flask, render_template, request, jsonify, send_file
import re
import requests
from hashlib import md5
from random import random
from urllib.parse import urlparse, urlunparse
from html import unescape
import yt_dlp
import os
import time
import threading
import glob
import json
from datetime import datetime, timedelta
import shutil
from flask_socketio import SocketIO, emit
from rich.console import Console

app = Flask(__name__)
app.config['SECRET_KEY'] = 'MrGadhvii!'
socketio = SocketIO(app, cors_allowed_origins="*")
console = Console()

# Load config
CONFIG_FILE = 'config.json'
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'download_path': 'downloads'}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

config = load_config()

def log_message(msg, type="info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[{timestamp}] {msg}")
    socketio.emit('server_log', {'message': msg, 'type': type, 'timestamp': timestamp})

class FileCleaner:
    def __init__(self, interval=15):
        self.interval = interval
        self.running = True
        self.paused = True  # Start paused by default
        self.last_clean = None
        self._lock = threading.Lock()
        
    def clean_temp_files(self):
        """Clean temporary download files"""
        while self.running:
            try:
                # Sleep if paused
                if self.paused:
                    time.sleep(1)
                    continue
                    
                self.last_clean = datetime.now()
                log_message("Starting cleanup cycle...")
                
                # Get absolute path to downloads directory
                downloads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
                log_message(f"Checking directory: {downloads_path}")
                
                if os.path.exists(downloads_path):
                    files = os.listdir(downloads_path)
                    log_message(f"Found {len(files)} files to check")
                    
                    for file in files:
                        if self.paused:
                            log_message("Cleanup interrupted - New download started")
                            break
                            
                        file_path = os.path.join(downloads_path, file)
                        try:
                            # Skip pure .mp4 files
                            if file.endswith('.mp4') and not any(x in file for x in ['-Frag', '.f', '.part', '.ytdl']):
                                continue
                                
                            # Remove fragment and temp files
                            if (file.endswith('.ytdl') or 
                                file.endswith('.part') or 
                                file.startswith('.') or 
                                'fragment' in file.lower() or 
                                '-frag' in file.lower() or
                                file.endswith('.f1') or 
                                file.endswith('.f2') or 
                                file.endswith('.frag') or
                                '.temp.' in file.lower() or
                                bool(re.search(r'\.mp4-Frag\d+$', file, re.IGNORECASE))):
                                
                                if os.path.isfile(file_path):
                                    os.unlink(file_path)
                                    log_message(f"Removed fragment file: {file}")
                                elif os.path.isdir(file_path):
                                    shutil.rmtree(file_path)
                                    log_message(f"Removed directory: {file}")
                                
                        except Exception as e:
                            log_message(f"Error cleaning {file}: {str(e)}")
                
                # Pause after one cleaning cycle
                self.paused = True
                log_message("Cleanup complete. Cleaner paused until next download completion.")
                    
            except Exception as e:
                log_message(f"Cleaner error: {str(e)}")
                self.paused = True

    def start(self):
        """Start the cleaner thread"""
        self.running = True
        self.thread = threading.Thread(target=self.clean_temp_files, daemon=True)
        self.thread.start()
        log_message("File cleaner started")

    def stop(self):
        """Stop the cleaner thread"""
        self.running = False
        log_message("File cleaner stopped")

# Initialize cleaner
cleaner = FileCleaner(interval=15)
cleaner.start()

@app.route('/cleaner/status')
def cleaner_status():
    """Get cleaner status"""
    if cleaner.last_clean:
        last_clean = cleaner.last_clean.strftime("%H:%M:%S")
        next_clean = (cleaner.last_clean + timedelta(seconds=cleaner.interval)).strftime("%H:%M:%S")
    else:
        last_clean = "Never"
        next_clean = "Soon"
    
    return jsonify({
        'running': cleaner.running,
        'last_clean': last_clean,
        'next_clean': next_clean,
        'interval': cleaner.interval
    })

@app.route('/config', methods=['POST'])
def update_config():
    try:
        data = request.get_json()
        download_path = data.get('download_path')
        
        if not download_path:
            return jsonify({'error': 'Download path is required'}), 400
            
        # Create directory if it doesn't exist
        os.makedirs(download_path, exist_ok=True)
        
        # Update config
        config['download_path'] = download_path
        save_config(config)
        
        return jsonify({'status': 'success', 'message': 'Configuration updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def prepare_dl(guid, context_id, secret, server_id, quality, embed_url, session):
    """Prepare download with proper ping and activation sequence"""
    try:
        def ping(time: int, paused: str, res: str):
            md5_hash = md5(f'{secret}_{context_id}_{time}_{paused}_{res}'.encode('utf8')).hexdigest()
            params = {
                'hash': md5_hash,
                'time': time,
                'paused': paused,
                'chosen_res': res
            }
            session.get(
                f'https://video-{server_id}.mediadelivery.net/.drm/{context_id}/ping',
                params=params,
                headers={
                    'authority': f'video-{server_id}.mediadelivery.net',
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'origin': 'https://iframe.mediadelivery.net',
                    'referer': 'https://iframe.mediadelivery.net/'
                }
            )

        def activate():
            session.get(
                f'https://video-{server_id}.mediadelivery.net/.drm/{context_id}/activate',
                headers={
                    'authority': f'video-{server_id}.mediadelivery.net',
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'origin': 'https://iframe.mediadelivery.net',
                    'referer': 'https://iframe.mediadelivery.net/'
                }
            )

        def main_playlist():
            params = {'contextId': context_id, 'secret': secret}
            response = session.get(
                f'https://iframe.mediadelivery.net/{guid}/playlist.drm',
                params=params,
                headers={
                    'authority': 'iframe.mediadelivery.net',
                    'accept': '*/*',
                    'accept-language': 'en-US,en;q=0.9',
                    'referer': embed_url
                }
            )
            resolutions = re.findall(r'RESOLUTION=(.*)', response.text)[::-1]
            if not resolutions:
                return quality
            return resolutions[0]

        def video_playlist():
            params = {'contextId': context_id}
            session.get(
                f'https://iframe.mediadelivery.net/{guid}/{quality}/video.drm',
                params=params
            )

        # Execute preparation sequence
        ping(time=0, paused='true', res='0')
        activate()
        resolution = main_playlist()
        video_playlist()
        
        # Send ping sequence
        for i in range(0, 29, 4):
            ping(time=i + round(random(), 6), paused='false', res=resolution.split('x')[-1])
        
        return True
    except Exception as e:
        print(f"Prepare download error: {str(e)}")
        return False

def download_video(url, quality, guid, context_id, secret, server_id, embed_url, file_name):
    """Download video using yt-dlp"""
    try:
        # Ensure cleaner is paused during download
        cleaner.paused = True
        log_message("Download started - Cleaner paused")
        
        # Setup session
        user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        session = requests.session()
        session.headers.update({
            'user-agent': user_agent,
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'origin': 'https://iframe.mediadelivery.net',
            'referer': embed_url
        })

        # Prepare download
        prepared = prepare_dl(guid, context_id, secret, server_id, quality, embed_url, session)
        if not prepared:
            raise Exception("Failed to prepare download")

        # Setup download path in project directory
        download_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        os.makedirs(download_path, exist_ok=True)
        
        # Setup yt-dlp options
        ydl_opts = {
            'format': 'best',
            'http_headers': {
                'Referer': embed_url,
                'User-Agent': user_agent
            },
            'concurrent_fragment_downloads': 10,
            'nocheckcertificate': True,
            'outtmpl': os.path.join(download_path, file_name),
            'restrictfilenames': True,
            'windowsfilenames': True,
            'nopart': True,
            'retries': float('inf'),
            'fragment_retries': float('inf'),
            'skip_unavailable_fragments': False,
            'no_warnings': True,
        }

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # If download successful
        log_message("Download completed successfully")
        log_message("Starting cleanup of temporary files...")
        cleaner.paused = False  # This will trigger one cleanup cycle
        return True, os.path.join(download_path, file_name)
        
    except Exception as e:
        log_message(f"Download error: {str(e)}")
        return False, str(e)

def analyze_bunny_url(url):
    results = {
        'status': 'Processing...',
        'messages': [],
        'urls': {}
    }
    
    try:
        # Step 1: Process URL
        results['messages'].append("Processing URL...")
        url_components = urlparse(url)
        clean_url = urlunparse((url_components.scheme, url_components.netloc, url_components.path, '', '', ''))
        guid = url_components.path.split('/')[-1]
        
        # Step 2: Setup session
        results['messages'].append("Setting up connection...")
        session = requests.session()
        session.headers.update({
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9'
        })
        
        # Step 3: Get embed page
        results['messages'].append("Fetching video information...")
        embed_page = session.get(clean_url).text
        
        # Step 4: Extract information
        results['messages'].append("Extracting server details...")
        server_id = re.search(r'https://video-(.*?)\.mediadelivery\.net', embed_page).group(1)
        
        results['messages'].append("Extracting security tokens...")
        search = re.search(r'contextId=(.*?)&secret=(.*?)"', embed_page)
        if not search:
            raise Exception("Could not find context and secret")
        context_id = search.group(1)
        secret = search.group(2)
        
        # Step 5: Extract title
        results['messages'].append("Getting video title...")
        title_match = re.search(r'og:title" content="(.*?)"', embed_page)
        if title_match:
            file_name = unescape(title_match.group(1))
            # If filename looks like a UUID/lecture ID, keep it as is
            if not re.match(r'^[\w-]+$', file_name):
                file_name = re.sub(r'[^\w\-_\. ]', '', file_name)
            file_name = file_name + '.mp4'
            results['title'] = "Video Title: " + file_name
            results['file_name'] = file_name
        
        # Store necessary info for download
        results['guid'] = guid
        results['context_id'] = context_id
        results['secret'] = secret
        results['server_id'] = server_id
        
        # Step 6: Get available qualities
        results['messages'].append("Finding available qualities...")
        params = {'contextId': context_id, 'secret': secret}
        playlist = session.get(
            f'https://iframe.mediadelivery.net/{guid}/playlist.drm',
            params=params,
            headers={
                'authority': 'iframe.mediadelivery.net',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'referer': clean_url
            }
        )
        
        # Extract resolutions and create quality mapping
        resolutions = re.findall(r'RESOLUTION=(\d+x\d+)', playlist.text)[::-1]
        quality_map = {}
        for res in resolutions:
            width = int(res.split('x')[0])
            if width >= 1920:
                quality = "1080p"
            elif width >= 1280:
                quality = "720p"
            elif width >= 854:
                quality = "480p"
            elif width >= 640:
                quality = "360p"
            else:
                quality = "240p"
            quality_map[quality] = res

        # Generate URLs for each quality
        results['messages'].append("Generating quality URLs...")
        for quality, resolution in quality_map.items():
            url = f'https://iframe.mediadelivery.net/{guid}/{resolution}/video.drm?contextId={context_id}&secret={secret}'
            results['urls'][quality] = {
                'url': url,
                'resolution': resolution
            }
        
        results['status'] = 'Success'
        results['messages'].append("✅ Analysis complete!")
        
    except Exception as e:
        results['status'] = 'Error'
        results['messages'].append(f"❌ Error: {str(e)}")
    
    return results

@app.route('/')
def index():
    return render_template('bunny.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    results = analyze_bunny_url(url)
    return jsonify(results)

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url')
        quality = data.get('quality')
        guid = data.get('guid')
        context_id = data.get('context_id')
        secret = data.get('secret')
        server_id = data.get('server_id')
        embed_url = data.get('embed_url')
        file_name = data.get('file_name')

        if not all([url, quality, guid, context_id, secret, server_id, embed_url, file_name]):
            return jsonify({'error': 'Missing required parameters'}), 400

        success, result = download_video(
            url, quality, guid, context_id, secret, 
            server_id, embed_url, file_name
        )

        if success:
            return jsonify({
                'status': 'success',
                'message': 'Download completed successfully',
                'file': result
            })
        else:
            return jsonify({
                'status': 'error',
                'message': f'Download failed: {result}'
            }), 500

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@socketio.on('connect')
def handle_connect():
    log_message("🟢 New client connected", "success")

@socketio.on('disconnect')
def handle_disconnect():
    log_message("🔴 Client disconnected", "warning")

class YTDLLogger:
    def debug(self, msg):
        if msg.startswith('[download]'):
            # Parse progress information
            try:
                if 'of ~' in msg:
                    # Fragment download
                    current, total = map(int, msg.split('of ~')[0].split('[download] ')[1].split('/'))
                    socketio.emit('download_progress', {
                        'type': 'fragment',
                        'current': current,
                        'total': total
                    })
                elif 'ETA' in msg:
                    # Overall progress
                    parts = msg.split()
                    percent = float(parts[1].replace('%', ''))
                    speed = parts[5]
                    eta = parts[7]
                    socketio.emit('download_progress', {
                        'type': 'overall',
                        'percent': percent,
                        'speed': speed,
                        'eta': eta
                    })
            except:
                pass
        log_message(msg)

@socketio.on('start_download')
def handle_download(data):
    try:
        url = data['url']
        quality = data['quality']
        filename = data['filename']
        
        log_message(f"Starting download: {filename}")
        # Your existing download code here, modified to use Socket.IO
        
        socketio.emit('download_started', {
            'filename': filename,
            'quality': quality
        })
        
        # ... rest of download logic ...
        
    except Exception as e:
        log_message(f"Download error: {str(e)}", "error")
        socketio.emit('download_error', {'error': str(e)})

@socketio.on('cancel_download')
def handle_cancel():
    # Implement download cancellation logic
    log_message("Download cancelled by user", "warning")
    socketio.emit('download_cancelled')

@app.route('/clear-cache', methods=['POST'])
def clear_cache():
    try:
        downloads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        cleaned_count = 0
        cleaned_size = 0

        for filename in os.listdir(downloads_path):
            # Skip MP4 files
            if filename.lower().endswith('.mp4'):
                continue
                
            file_path = os.path.join(downloads_path, filename)
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                continue
            
            try:
                size = os.path.getsize(file_path)
                os.remove(file_path)
                cleaned_count += 1
                cleaned_size += size
            except Exception as e:
                print(f"Error cleaning {filename}: {str(e)}")

        # Format size
        size_str = format_size(cleaned_size)
        message = f"Cleaned {cleaned_count} temporary files ({size_str})"
        return jsonify({'message': message, 'success': True})
        
    except Exception as e:
        return jsonify({'message': f"Error: {str(e)}", 'success': False}), 500

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

if __name__ == '__main__':
    try:
        downloads_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
        if not os.path.exists(downloads_path):
            os.makedirs(downloads_path)
            log_message(f"Created downloads directory: {downloads_path}")
            
        log_message("🚀 Starting BunnyCDN Downloader Server")
        log_message("📝 Created by MrGadhvii")
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
    finally:
        cleaner.stop()
        log_message("Server stopped") 