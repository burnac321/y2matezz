from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import yt_dlp
import os
import threading
import time
import uuid
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
DOWNLOAD_FOLDER = 'downloads'
MAX_FILE_AGE = 3600  # 1 hour in seconds

# Supported platforms
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be',
    'facebook.com', 'fb.watch',
    'instagram.com',
    'tiktok.com',
    'twitter.com', 'x.com',
    'vimeo.com',
    'dailymotion.com',
    'twitch.tv',
    'reddit.com',
    'bilibili.com',
    'nicovideo.jp'
]

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def cleanup_old_files():
    """Remove files older than MAX_FILE_AGE"""
    try:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > MAX_FILE_AGE:
                    os.remove(file_path)
                    logger.info(f"Removed old file: {filename}")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

def is_supported_url(url):
    """Check if URL is from supported platform"""
    try:
        domain = urlparse(url).netloc.lower()
        return any(platform in domain for platform in SUPPORTED_PLATFORMS)
    except:
        return False

def sanitize_filename(filename):
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:100]  # Limit filename length

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_video_info():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        video_url = data['url'].strip()
        
        if not video_url:
            return jsonify({'error': 'Empty URL provided'}), 400
        
        if not is_supported_url(video_url):
            return jsonify({'error': 'Platform not supported or invalid URL'}), 400
        
        # yt-dlp options for info extraction only
        ydl_opts = {
            'quiet': True,
            'no_warnings': False,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            
            # Get available formats
            formats = []
            if 'formats' in info:
                for f in info['formats']:
                    if f.get('vcodec') != 'none' and f.get('acodec') != 'none':  # Video with audio
                        format_info = {
                            'format_id': f['format_id'],
                            'ext': f.get('ext', 'mp4'),
                            'quality': f.get('format_note', 'unknown'),
                            'width': f.get('width'),
                            'height': f.get('height'),
                            'filesize': f.get('filesize') or f.get('filesize_approx'),
                            'vcodec': f.get('vcodec'),
                            'acodec': f.get('acodec')
                        }
                        # Only add if we have reasonable quality info
                        if format_info['width'] or format_info['height'] or format_info['quality'] != 'unknown':
                            formats.append(format_info)
            
            # Sort formats by quality (rough estimate)
            formats.sort(key=lambda x: (
                x['width'] or 0,
                x['height'] or 0,
                x['filesize'] or 0
            ), reverse=True)
            
            response_data = {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration'),
                'thumbnail': info.get('thumbnail'),
                'uploader': info.get('uploader'),
                'view_count': info.get('view_count'),
                'formats': formats[:10]  # Limit to top 10 formats
            }
            
            return jsonify(response_data)
            
    except Exception as e:
        logger.error(f"Info extraction error: {str(e)}")
        return jsonify({'error': f'Failed to get video info: {str(e)}'}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        video_url = data['url'].strip()
        format_id = data.get('format', 'best')
        
        if not video_url:
            return jsonify({'error': 'Empty URL provided'}), 400
        
        if not is_supported_url(video_url):
            return jsonify({'error': 'Platform not supported'}), 400
        
        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        
        # yt-dlp options for download
        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, f'%(title)s_{file_id}.%(ext)s'),
            'format': format_id,
            'merge_output_format': 'mp4',
            'quiet': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First get info to know the filename
            info = ydl.extract_info(video_url, download=False)
            original_filename = ydl.prepare_filename(info)
            
            # Download the video
            ydl.download([video_url])
            
            # The actual filename after download
            actual_filename = os.path.basename(original_filename)
            file_path = os.path.join(DOWNLOAD_FOLDER, actual_filename)
            
            if not os.path.exists(file_path):
                return jsonify({'error': 'Download failed - file not created'}), 500
            
            # Return file info for download
            return jsonify({
                'success': True,
                'filename': actual_filename,
                'title': info.get('title', 'video'),
                'download_url': f'/api/file/{actual_filename}'
            })
            
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/file/<filename>')
def download_file(filename):
    try:
        # Security check - prevent directory traversal
        if '..' in filename or filename.startswith('/'):
            return jsonify({'error': 'Invalid filename'}), 400
            
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Trigger cleanup after download
        threading.Thread(target=cleanup_old_files).start()
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return jsonify({'error': 'File download failed'}), 500

@app.route('/api/supported-platforms')
def supported_platforms():
    return jsonify({
        'platforms': SUPPORTED_PLATFORMS,
        'count': len(SUPPORTED_PLATFORMS)
    })

if __name__ == '__main__':
    # Initial cleanup
    cleanup_old_files()
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
