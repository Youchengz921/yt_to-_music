"""
YouTube/Playlist to MP3 Converter
Flask web application
"""
import os
import shutil
import zipfile
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory

from utils.downloader import extract_playlist_info, download_as_mp3, download_media, format_duration, ensure_ffmpeg
from utils.similarity import find_duplicates

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yt-to-mp3-secret-key'

DOWNLOADS_DIR = Path(__file__).parent / "downloads"

# Store selected folder path from dialog
selected_folder_path = None

# Store last used download path for ZIP functionality
last_download_path = None


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/browse-folder', methods=['POST'])
def browse_folder():
    """
    Open a folder selection dialog using tkinter
    Returns the selected folder path
    """
    global selected_folder_path
    
    def open_dialog():
        global selected_folder_path
        try:
            import tkinter as tk
            from tkinter import filedialog
            
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            root.attributes('-topmost', True)  # Bring dialog to front
            
            folder_path = filedialog.askdirectory(
                title='選擇下載資料夾',
                mustexist=False
            )
            
            root.destroy()
            selected_folder_path = folder_path if folder_path else None
        except Exception as e:
            print(f"Dialog error: {e}")
            selected_folder_path = None
    
    # Run dialog in a separate thread to avoid blocking
    dialog_thread = threading.Thread(target=open_dialog)
    dialog_thread.start()
    dialog_thread.join(timeout=60)  # Wait up to 60 seconds
    
    if selected_folder_path:
        return jsonify({'path': selected_folder_path})
    else:
        return jsonify({'path': None, 'error': 'No folder selected'})


@app.route('/api/fetch-info', methods=['POST'])
def fetch_info():
    """
    Fetch video info from URL(s)
    Supports playlist URLs and multiple single video URLs
    """
    data = request.get_json()
    urls = data.get('urls', [])
    limit = data.get('limit')  # Optional limit for Mix playlists
    
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400
    
    all_videos = []
    errors = []
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
        
        try:
            videos = extract_playlist_info(url)
            if videos:
                # Apply per-URL or total limit if needed (simplest is total limit at end, 
                # but per-playlist limit during extraction would be faster if supported by backend.
                # Here we just collect all and slice later for simplicity, same as GUI app initially did)
                all_videos.extend(videos)
                
                # Optimization: Stop if we already exceed limit significantly
                if limit and len(all_videos) > int(limit) + 50:
                    break
            else:
                errors.append(f"Could not extract info from: {url}")
        except Exception as e:
            errors.append(f"Error processing {url}: {str(e)}")
    
    # Apply strict limit
    if limit:
        try:
            limit_val = int(limit)
            if len(all_videos) > limit_val:
                all_videos = all_videos[:limit_val]
        except:
            pass
    
    if not all_videos:
        return jsonify({'error': 'No videos found', 'details': errors}), 400
    
    # Add formatted duration to each video
    for video in all_videos:
        video['duration_formatted'] = format_duration(video.get('duration', 0))
    
    return jsonify({
        'videos': all_videos,
        'count': len(all_videos),
        'errors': errors if errors else None
    })


@app.route('/api/check-duplicates', methods=['POST'])
def check_duplicates():
    """
    Check for duplicate songs based on title similarity
    """
    data = request.get_json()
    videos = data.get('videos', [])
    threshold = data.get('threshold', 80)
    
    if not videos:
        return jsonify({'error': 'No videos provided'}), 400
    
    duplicate_groups, duplicate_indices = find_duplicates(videos, threshold)
    
    # Convert sets to lists for JSON serialization
    return jsonify({
        'duplicate_groups': duplicate_groups,
        'duplicate_indices': list(duplicate_indices)
    })


@app.route('/api/download', methods=['POST'])
def download():
    """
    Download selected videos as MP3/MP4/M4A
    """
    data = request.get_json()
    videos = data.get('videos', [])
    custom_path = data.get('download_path', '').strip()
    output_format = data.get('format', 'mp3')  # Default to mp3
    
    if not videos:
        return jsonify({'error': 'No videos selected'}), 400
    
    # Ensure ffmpeg is ready
    try:
        ensure_ffmpeg()
    except Exception as e:
        return jsonify({'error': f'FFmpeg setup failed: {str(e)}'}), 500
    
    # Determine download directory
    global last_download_path
    if custom_path:
        download_dir = Path(custom_path)
        try:
            download_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return jsonify({'error': f'無法建立資料夾: {str(e)}'}), 400
    else:
        download_dir = DOWNLOADS_DIR
        # Clean default downloads directory
        if download_dir.exists():
            shutil.rmtree(download_dir)
        download_dir.mkdir(parents=True, exist_ok=True)
    
    # Store for ZIP download
    last_download_path = download_dir
    
    # Parallel download function
    def download_single(video):
        video_id = video.get('id', '')
        title = video.get('title', 'Unknown')
        url = video.get('url', '')
        
        if not url:
            return {'title': title, 'success': False, 'error': 'No URL', 'video': video}
        
        try:
            path = download_media(url, video_id, title, download_dir, output_format)
            if path:
                return {
                    'title': title,
                    'success': True,
                    'filename': os.path.basename(path)
                }
            else:
                return {'title': title, 'success': False, 'error': 'Download failed', 'video': video}
        except Exception as e:
            return {'title': title, 'success': False, 'error': str(e), 'video': video}
    
    # Use ThreadPoolExecutor for parallel downloads (3 concurrent)
    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = []
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(download_single, v): v for v in videos}
        for future in as_completed(futures):
            results.append(future.result())
    
    successful = [r for r in results if r.get('success')]
    
    return jsonify({
        'results': results,
        'successful_count': len(successful),
        'total_count': len(videos),
        'download_path': str(download_dir),
        'format': output_format
    })


@app.route('/api/download-zip', methods=['GET'])
def download_zip():
    """
    Create and send a ZIP file containing all downloaded MP3s
    """
    # Use last download path or default
    download_dir = last_download_path if last_download_path else DOWNLOADS_DIR
    
    if not download_dir.exists():
        return jsonify({'error': 'No downloads available'}), 404
    
    mp3_files = list(download_dir.glob('*.mp3'))
    if not mp3_files:
        return jsonify({'error': 'No MP3 files found'}), 404
    
    zip_path = download_dir / 'songs.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for mp3 in mp3_files:
            zf.write(mp3, mp3.name)
    
    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name='youtube_songs.zip'
    )


@app.route('/downloads/<path:filename>')
def serve_download(filename):
    """Serve individual MP3 files"""
    # Use last_download_path if set, otherwise default
    directory = last_download_path if last_download_path else DOWNLOADS_DIR
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == '__main__':
    print("=" * 50)
    print("YouTube/Playlist to MP3 Converter")
    print("=" * 50)
    print("\nStarting server...")
    # Get local IP
    import socket
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        # Try to find a real LAN IP if localhost is returned
        if local_ip.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
    except:
        local_ip = "127.0.0.1"

    print(f"Open http://localhost:5000 in your browser")
    print(f"Or on your phone (same Wi-Fi): http://{local_ip}:5000\n")
    
    # Ensure ffmpeg is ready on startup
    try:
        ensure_ffmpeg()
    except Exception as e:
        print(f"Warning: Could not setup FFmpeg: {e}")
    
    app.run(debug=True, port=5000, host='0.0.0.0')
