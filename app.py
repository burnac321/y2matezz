from flask import Flask, request, jsonify
import subprocess
import json
import os
import re
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def sanitize_filename(name):
    """Remove invalid characters from filename"""
    return re.sub(r'[<>:"/\\|?*]', '', name)

@app.route('/get_formats', methods=['POST'])
def get_formats():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Get video info using yt-dlp
        result = subprocess.run([
            'yt-dlp', '-j', '--no-playlist', '--no-warnings', url
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return jsonify({'error': 'Video not found or URL not supported'}), 400
            
        video_info = json.loads(result.stdout)
        
        formats = []
        for f in video_info.get('formats', []):
            if f.get('url'):
                formats.append({
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution', 'audio'),
                    'filesize': f.get('filesize'),
                    'note': f.get('format_note', '')
                })
        
        return jsonify({
            'title': sanitize_filename(video_info.get('title', 'video')),
            'thumbnail': video_info.get('thumbnail'),
            'duration': video_info.get('duration_string'),
            'formats': formats[:15]
        })
        
    except Exception as e:
        return jsonify({'error': 'Server error'}), 500

@app.route('/get_direct_url', methods=['POST'])
def get_direct_url():
    try:
        data = request.get_json()
        url = data.get('url')
        format_id = data.get('format_id', 'best')
        
        # Get direct URL using yt-dlp -g
        result = subprocess.run([
            'yt-dlp', '-g', '--no-playlist', '-f', format_id, url
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            return jsonify({'error': 'Failed to get download URL'}), 400
            
        direct_url = result.stdout.strip().split('\n')[0]
        
        return jsonify({
            'video_url': direct_url,
            'filename': 'video.mp4'
        })
        
    except Exception as e:
        return jsonify({'error': 'Server error'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'service': 'Y2MateZZ API'})

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Y2MateZZ Video Downloader API',
        'endpoints': {
            '/get_formats': 'POST - Get available formats',
            '/get_direct_url': 'POST - Get download link'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
