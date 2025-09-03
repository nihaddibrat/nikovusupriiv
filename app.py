from flask import Flask, render_template, request, jsonify, send_file
import os
import re
import requests
from datetime import datetime
import tempfile
from pytube import YouTube
import json

app = Flask(__name__)

# Temp directory
DOWNLOAD_FOLDER = tempfile.gettempdir()

def clean_filename(filename):
    """Fayl adını təmizlə"""
    filename = re.sub(r'[^\w\s-]', '', filename)
    filename = re.sub(r'[-\s]+', '-', filename)
    return filename[:100]

def download_youtube(url, format_type='video'):
    """YouTube video endir"""
    try:
        yt = YouTube(url)
        filename = clean_filename(yt.title) + "_" + datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format_type == 'audio':
            stream = yt.streams.filter(only_audio=True).first()
            filename += '.mp3'
        else:
            stream = yt.streams.get_highest_resolution()
            filename += '.mp4'
        
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        stream.download(output_path=DOWNLOAD_FOLDER, filename=filename)
        
        return filepath
    except Exception as e:
        print(f"YouTube download error: {str(e)}")
        return None

def download_tiktok(url):
    """TikTok video endir"""
    try:
        # TikTok API endpoint
        api_url = "https://api.tiklydown.eu.org/api/download/v3"
        params = {"url": url}
        
        response = requests.get(api_url, params=params, timeout=30)
        data = response.json()
        
        if data.get('result') and data['result'].get('video'):
            video_url = data['result']['video']
            
            # Video endir
            video_response = requests.get(video_url, stream=True)
            filename = f"tiktok_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
    except Exception as e:
        print(f"TikTok download error: {str(e)}")
    return None

def download_instagram(url):
    """Instagram video endir"""
    try:
        # Instagram API endpoint
        api_url = "https://api.downloadgram.org/media"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        data = {'url': url}
        
        response = requests.post(api_url, data=data, headers=headers, timeout=30)
        result = response.json()
        
        if result.get('media_url'):
            video_url = result['media_url']
            
            # Video endir
            video_response = requests.get(video_url, stream=True)
            filename = f"instagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = os.path.join(DOWNLOAD_FOLDER, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in video_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return filepath
    except Exception as e:
        print(f"Instagram download error: {str(e)}")
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
        
        # Platform təyin et
        platform = "Video"
        title = "Video"
        
        if "youtube.com" in url or "youtu.be" in url:
            try:
                yt = YouTube(url)
                title = yt.title
                platform = "YouTube"
            except:
                title = "YouTube Video"
                platform = "YouTube"
        elif "tiktok.com" in url:
            platform = "TikTok"
            title = "TikTok Video"
        elif "instagram.com" in url:
            platform = "Instagram"
            title = "Instagram Video"
        elif "twitter.com" in url or "x.com" in url:
            platform = "Twitter/X"
            title = "Twitter Video"
        
        return jsonify({
            'success': True,
            'info': {
                'title': title,
                'duration': 0,
                'thumbnail': '',
                'platform': platform
            }
        })
            
    except Exception as e:
        print(f"Info error: {str(e)}")
        return jsonify({'error': 'Video məlumatları alına bilmədi'}), 400

@app.route('/api/download', methods=['POST'])
def download():
    """Video endir"""
    try:
        data = request.json
        url = data.get('url')
        format_type = data.get('format', 'video')
        
        if not url:
            return jsonify({'error': 'URL tələb olunur'}), 400
        
        filepath = None
        
        # YouTube
        if "youtube.com" in url or "youtu.be" in url:
            filepath = download_youtube(url, format_type)
        
        # TikTok
        elif "tiktok.com" in url:
            filepath = download_tiktok(url)
        
        # Instagram
        elif "instagram.com" in url:
            filepath = download_instagram(url)
        
        # Twitter - Alternativ API
        elif "twitter.com" in url or "x.com" in url:
            # Twitter üçün başqa API lazımdır
            return jsonify({'error': 'Twitter hazırda dəstəklənmir'}), 400
        
        else:
            return jsonify({'error': 'Dəstəklənməyən platforma'}), 400
        
        if filepath and os.path.exists(filepath):
            return send_file(
                filepath,
                as_attachment=True,
                download_name=os.path.basename(filepath),
                mimetype='application/octet-stream'
            )
        else:
            return jsonify({'error': 'Video endiriləmədi'}), 500
            
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': 'Server xətası baş verdi'}), 500

@app.route('/api/clean', methods=['POST'])
def clean_downloads():
    """Köhnə faylları təmizlə"""
    try:
        # Temp qovluğundaki köhnə faylları sil
        for filename in os.listdir(DOWNLOAD_FOLDER):
            if filename.startswith(('youtube_', 'tiktok_', 'instagram_', 'download_')):
                filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                try:
                    os.remove(filepath)
                except:
                    pass
        return jsonify({'success': True})
    except:
        return jsonify({'success': True})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
