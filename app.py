from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import re
from pathlib import Path
import json

app = Flask(__name__)

# Download qovluğunu yarat
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def clean_filename(filename):
    """Fayl adını təmizlə"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename[:200]  # Max 200 simvol

def get_video_info(url):
    """Video məlumatlarını al"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
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
        return None

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
        
        info = get_video_info(url)
        if info:
            return jsonify({'success': True, 'info': info})
        else:
            return jsonify({'error': 'Video məlumatları alına bilmədi'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """Video və ya audio endir"""
    try:
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'video')  # 'video' və ya 'audio'
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        # Fayl adını təyin et
        filename = f"{clean_filename('download')}_{os.urandom(4).hex()}"
        
        if format_type == 'audio':
            # MP3 formatında endir
            output_path = os.path.join(DOWNLOAD_FOLDER, f"{filename}.mp3")
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            }
        else:
            # Video formatında endir
            output_path = os.path.join(DOWNLOAD_FOLDER, f"{filename}.mp4")
            if quality == 'best':
                format_string = 'best[ext=mp4]/best'
            else:
                format_string = f'best[height<={quality}][ext=mp4]/best[height<={quality}]/best'
            
            ydl_opts = {
                'format': format_string,
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
            }
        
        # Endirmə prosesi
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Faylı tap
        files = list(Path(DOWNLOAD_FOLDER).glob(f"{filename}.*"))
        if files:
            file_path = str(files[0])
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'Fayl tapılmadı'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clean', methods=['POST'])
def clean_downloads():
    """Köhnə faylları sil"""
    try:
        for file in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)