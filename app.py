from flask import Flask, render_template, request, jsonify, send_file
import subprocess
import os
import json
import tempfile
from datetime import datetime
import re

app = Flask(__name__)

# Temp directory
DOWNLOAD_FOLDER = tempfile.gettempdir()

def clean_filename(filename):
    """Fayl adını təmizlə"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename[:100]

def get_video_info(url):
    """yt-dlp ilə video məlumatlarını al"""
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-playlist',
            '--no-warnings',
            '--quiet',
            '--no-check-certificate',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            info = json.loads(result.stdout)
            return {
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', ''),
                'view_count': info.get('view_count', 0)
            }
    except Exception as e:
        print(f"Info error: {str(e)}")
    return None

def download_video(url, format_type='video', quality='best'):
    """yt-dlp ilə video endir"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'audio':
            filename = f"audio_{timestamp}.mp3"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            cmd = [
                'yt-dlp',
                '-x',  # Extract audio
                '--audio-format', 'mp3',
                '--audio-quality', '192K',
                '--no-playlist',
                '--no-check-certificate',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--output', filepath,
                url
            ]
        else:
            filename = f"video_{timestamp}.mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            # Quality seçimi
            if quality == 'best':
                format_string = 'best[ext=mp4]/best'
            elif quality == '1080':
                format_string = 'best[height<=1080][ext=mp4]/best[height<=1080]/best'
            elif quality == '720':
                format_string = 'best[height<=720][ext=mp4]/best[height<=720]/best'
            elif quality == '480':
                format_string = 'best[height<=480][ext=mp4]/best[height<=480]/best'
            else:
                format_string = 'best[height<=360][ext=mp4]/best[height<=360]/best'
            
            cmd = [
                'yt-dlp',
                '-f', format_string,
                '--no-playlist',
                '--no-check-certificate',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--merge-output-format', 'mp4',
                '--output', filepath,
                url
            ]
        
        # Endirmə prosesi
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0 and os.path.exists(filepath):
            return filepath
        else:
            print(f"yt-dlp error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("Download timeout")
        return None
    except Exception as e:
        print(f"Download error: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def api_get_info():
    """Video məlumatlarını API endpoint"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        # Video məlumatlarını al
        info = get_video_info(url)
        
        if info:
            return jsonify({
                'success': True,
                'info': info
            })
        else:
            # Məlumat alınmasa da, sadə cavab göndər
            return jsonify({
                'success': True,
                'info': {
                    'title': 'Video',
                    'duration': 0,
                    'thumbnail': '',
                    'uploader': '',
                    'view_count': 0
                }
            })
            
    except Exception as e:
        print(f"API info error: {str(e)}")
        return jsonify({'error': 'Video məlumatları alına bilmədi'}), 400

@app.route('/api/download', methods=['POST'])
def api_download():
    """Video endirmə API endpoint"""
    try:
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'video')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        # Video endir
        filepath = download_video(url, format_type, quality)
        
        if filepath and os.path.exists(filepath):
            # Fayl ölçüsünü yoxla
            file_size = os.path.getsize(filepath)
            if file_size > 200 * 1024 * 1024:  # 200MB limit
                os.remove(filepath)
                return jsonify({'error': 'Fayl çox böyükdür (max 200MB)'}), 413
            
            # Faylı göndər
            return send_file(
                filepath,
                as_attachment=True,
                download_name=os.path.basename(filepath),
                mimetype='application/octet-stream'
            )
        else:
            return jsonify({'error': 'Video endiriləmədi. Başqa link yoxlayın.'}), 500
            
    except Exception as e:
        print(f"API download error: {str(e)}")
        return jsonify({'error': 'Server xətası baş verdi'}), 500

@app.route('/api/clean', methods=['POST'])
def api_clean():
    """Köhnə faylları təmizlə"""
    try:
        count = 0
        for filename in os.listdir(DOWNLOAD_FOLDER):
            if filename.startswith(('video_', 'audio_')):
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                try:
                    os.remove(filepath)
                    count += 1
                except:
                    pass
        return jsonify({'success': True, 'cleaned': count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/health')
def health():
    """Health check"""
    try:
        # yt-dlp versiyasını yoxla
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        version = result.stdout.strip() if result.returncode == 0 else 'unknown'
        
        return jsonify({
            'status': 'healthy',
            'yt_dlp_version': version,
            'timestamp': datetime.now().isoformat()
        })
    except:
        return jsonify({'status': 'healthy'})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Səhifə tapılmadı'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server xətası'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
