import os
import certifi
# SSL sertifikat problemini həll et
os.environ['SSL_CERT_FILE'] = certifi.where()
os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()

from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import re
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time

app = Flask(__name__)

# Render üçün temp directory
DOWNLOAD_FOLDER = '/tmp/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def clean_filename(filename):
    """Fayl adını təmizlə"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename[:200]

def get_video_info(url):
    """Video məlumatlarını al"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'nocheckcertificate': True,  # SSL sertifikatını yoxlama
        'no_check_certificate': True,
        'verbose': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Video'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': info.get('formats', [])
            }
    except Exception as e:
        print(f"Error getting video info: {str(e)}")
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
        allowed_domains = ['youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com', 'x.com', 'instagram.com']
        if not any(domain in url for domain in allowed_domains):
            return jsonify({'error': 'Dəstəklənməyən platforma'}), 400
        
        info = get_video_info(url)
        if info:
            return jsonify({'success': True, 'info': info})
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
        allowed_domains = ['youtube.com', 'youtu.be', 'tiktok.com', 'twitter.com', 'x.com', 'instagram.com']
        if not any(domain in url for domain in allowed_domains):
            return jsonify({'error': 'Dəstəklənməyən platforma'}), 400
        
        # Unikal fayl adı yarat
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"download_{timestamp}_{os.urandom(4).hex()}"
        
        if format_type == 'audio':
            # MP3 formatında endir
            output_template = os.path.join(DOWNLOAD_FOLDER, f"{filename}.%(ext)s")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'no_check_certificate': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'max_filesize': 100 * 1024 * 1024,  # Max 100MB
            }
        else:
            # Video formatında endir
            output_template = os.path.join(DOWNLOAD_FOLDER, f"{filename}.%(ext)s")
            if quality == 'best':
                format_string = 'best[ext=mp4]/best'
            else:
                format_string = f'best[height<={quality}][ext=mp4]/best[height<={quality}]/best'
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': output_template,
                'quiet': True,
                'no_warnings': True,
                'nocheckcertificate': True,
                'no_check_certificate': True,
                'max_filesize': 200 * 1024 * 1024,  # Max 200MB
            }
        
        # Endirmə prosesi
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Endirilən faylı tap
        files = list(Path(DOWNLOAD_FOLDER).glob(f"{filename}.*"))
        if files:
            temp_file = str(files[0])
            
            # Fayl ölçüsünü yoxla
            file_size = os.path.getsize(temp_file)
            if file_size > 200 * 1024 * 1024:  # 200MB limit
                os.remove(temp_file)
                return jsonify({'error': 'Fayl çox böyükdür (max 200MB)'}), 413
            
            # Faylı göndər
            return send_file(
                temp_file,
                as_attachment=True,
                download_name=os.path.basename(temp_file),
                mimetype='application/octet-stream'
            )
        else:
            return jsonify({'error': 'Fayl endiriləmədi'}), 404
            
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'private' in error_msg.lower():
            return jsonify({'error': 'Bu video məxfidir'}), 403
        elif 'copyright' in error_msg.lower():
            return jsonify({'error': 'Müəllif hüququ səbəbindən endirilə bilməz'}), 403
        else:
            return jsonify({'error': 'Video endirilə bilmədi'}), 400
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
