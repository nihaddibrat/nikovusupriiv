import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from flask import Flask, render_template, request, jsonify, send_file
import requests
import re
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time
import json

app = Flask(__name__)

# Render üçün temp directory
DOWNLOAD_FOLDER = '/tmp/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Cobalt API endpoint
COBALT_API = "https://api.cobalt.tools/api/json"

def clean_filename(filename):
    """Fayl adını təmizlə"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename[:200]

def get_video_info_cobalt(url):
    """Cobalt API ilə video məlumatlarını al"""
    try:
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        payload = {
            "url": url,
            "vQuality": "720",
            "aFormat": "mp3",
            "isAudioOnly": False,
            "disableMetadata": False
        }
        
        response = requests.post(COBALT_API, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'stream' or data.get('status') == 'redirect':
                # Video məlumatlarını çıxar
                return {
                    'success': True,
                    'title': 'Video',
                    'download_url': data.get('url'),
                    'type': 'direct'
                }
            elif data.get('status') == 'picker':
                # Çoxlu format mövcuddur
                return {
                    'success': True,
                    'title': 'Video',
                    'picker': data.get('picker', []),
                    'type': 'picker'
                }
        return None
    except Exception as e:
        print(f"Cobalt API error: {str(e)}")
        return None

def download_from_url(url, filename):
    """URL-dən faylı endir"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, stream=True, timeout=60)
        response.raise_for_status()
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return filepath
    except Exception as e:
        print(f"Download error: {str(e)}")
        return None

def cleanup_old_files():
    """30 dəqiqədən köhnə faylları sil"""
    try:
        now = datetime.now()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(filepath):
                file_age = datetime.fromtimestamp(os.path.getmtime(filepath))
                if now - file_age > timedelta(minutes=30):
                    os.remove(filepath)
                    print(f"Deleted old file: {filename}")
    except Exception as e:
        print(f"Cleanup error: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    """Video məlumatlarını göndər"""
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        # URL doğrulama
        allowed_domains = ['youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com', 'x.com', 'instagram.com', 'facebook.com', 'vimeo.com']
        if not any(domain in url for domain in allowed_domains):
            return jsonify({'error': 'Dəstəklənməyən platforma'}), 400
        
        # Cobalt API ilə məlumat al
        info = get_video_info_cobalt(url)
        
        if info and info.get('success'):
            return jsonify({
                'success': True, 
                'info': {
                    'title': info.get('title', 'Video'),
                    'duration': 0,
                    'thumbnail': '',
                    'formats': []
                }
            })
        else:
            return jsonify({'error': 'Video məlumatları alına bilmədi'}), 400
            
    except Exception as e:
        print(f"API Error: {str(e)}")
        return jsonify({'error': 'Server xətası baş verdi'}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """Video və ya audio endir"""
    temp_file = None
    try:
        # Köhnə faylları təmizlə
        cleanup_old_files()
        
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'video')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        # URL doğrulama
        allowed_domains = ['youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com', 'x.com', 'instagram.com', 'facebook.com', 'vimeo.com']
        if not any(domain in url for domain in allowed_domains):
            return jsonify({'error': 'Dəstəklənməyən platforma'}), 400
        
        # Cobalt API ilə download linki al
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Quality mapping
        quality_map = {
            'best': 'max',
            '1080': '1080',
            '720': '720',
            '480': '480',
            '360': '360'
        }
        
        payload = {
            "url": url,
            "vQuality": quality_map.get(quality, '720'),
            "aFormat": "mp3",
            "isAudioOnly": format_type == 'audio',
            "disableMetadata": False
        }
        
        response = requests.post(COBALT_API, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'stream' or result.get('status') == 'redirect':
                download_url = result.get('url')
                
                if download_url:
                    # Fayl adını yarat
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    extension = 'mp3' if format_type == 'audio' else 'mp4'
                    filename = f"download_{timestamp}_{os.urandom(4).hex()}.{extension}"
                    
                    # Faylı endir
                    temp_file = download_from_url(download_url, filename)
                    
                    if temp_file and os.path.exists(temp_file):
                        # Fayl ölçüsünü yoxla
                        file_size = os.path.getsize(temp_file)
                        if file_size > 200 * 1024 * 1024:  # 200MB limit
                            os.remove(temp_file)
                            return jsonify({'error': 'Fayl çox böyükdür (max 200MB)'}), 413
                        
                        # Faylı göndər
                        return send_file(
                            temp_file,
                            as_attachment=True,
                            download_name=filename,
                            mimetype='application/octet-stream'
                        )
                    else:
                        return jsonify({'error': 'Fayl endiriləmədi'}), 500
                        
            elif result.get('status') == 'picker':
                # Birinci mövcud formatı seç
                picker = result.get('picker', [])
                if picker:
                    download_url = picker[0].get('url')
                    
                    if download_url:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        extension = 'mp3' if format_type == 'audio' else 'mp4'
                        filename = f"download_{timestamp}_{os.urandom(4).hex()}.{extension}"
                        
                        temp_file = download_from_url(download_url, filename)
                        
                        if temp_file and os.path.exists(temp_file):
                            file_size = os.path.getsize(temp_file)
                            if file_size > 200 * 1024 * 1024:
                                os.remove(temp_file)
                                return jsonify({'error': 'Fayl çox böyükdür (max 200MB)'}), 413
                            
                            return send_file(
                                temp_file,
                                as_attachment=True,
                                download_name=filename,
                                mimetype='application/octet-stream'
                            )
                            
            elif result.get('status') == 'error':
                error_msg = result.get('text', 'Naməlum xəta')
                return jsonify({'error': error_msg}), 400
                
        return jsonify({'error': 'Video endiriləmədi'}), 500
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Sorğu müddəti bitdi. Yenidən cəhd edin.'}), 504
    except Exception as e:
        print(f"Download Error: {str(e)}")
        return jsonify({'error': 'Server xətası baş verdi'}), 500
    finally:
        # Temp faylı sil
        if temp_file and os.path.exists(temp_file):
            try:
                def delayed_delete():
                    time.sleep(5)
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                threading.Thread(target=delayed_delete, daemon=True).start()
            except:
                pass

@app.route('/api/clean', methods=['POST'])
def clean_downloads():
    """Köhnə faylları sil"""
    try:
        cleanup_old_files()
        return jsonify({'success': True, 'message': 'Təmizləndi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Səhifə tapılmadı'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server xətası'}), 500

# Production üçün
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
