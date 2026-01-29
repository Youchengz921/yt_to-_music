"""
YouTube/Playlist downloader utility using yt-dlp
"""
import os
import yt_dlp
from pathlib import Path
from .ffmpeg_setup import get_ffmpeg_path, download_ffmpeg

DOWNLOADS_DIR = Path(__file__).parent.parent / "downloads"


def ensure_ffmpeg():
    """Ensure ffmpeg is available"""
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        ffmpeg_path = download_ffmpeg()
    return ffmpeg_path


def get_ydl_opts(ffmpeg_path=None):
    """Get yt-dlp options"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    if ffmpeg_path:
        opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
    return opts


def extract_playlist_info(url):
    """
    Extract info from a playlist or single video URL
    Returns list of video info dicts with: id, title, url, duration
    """
    # Highly optimized extraction options for speed
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',  # Only flatten playlists, get full info for single videos
        'skip_download': True,
        'ignoreerrors': True,  # Skip unavailable videos
        'socket_timeout': 5,   # Faster timeout
        'retries': 1,          # Minimal retries for speed
        'no_check_certificates': True,  # Skip SSL verification for speed
        'geo_bypass': True,    # Bypass geo restrictions
        'nocheckcertificate': True,
        'lazy_playlist': True,  # Don't fetch all entries at once
        'playlist_items': '1-200',  # Limit to first 200 for speed
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                return []
            
            # Check if it's a playlist
            if 'entries' in info:
                videos = []
                entries = info.get('entries', [])
                
                # Process entries (may be generator for large playlists)
                for entry in entries:
                    if entry:
                        vid_id = entry.get('id', '')
                        videos.append({
                            'id': vid_id,
                            'title': entry.get('title', 'Unknown'),
                            'url': entry.get('url') or f"https://www.youtube.com/watch?v={vid_id}",
                            'duration': entry.get('duration', 0),
                            'thumbnail': entry.get('thumbnail', '')
                        })
                return videos
            else:
                # Single video
                return [{
                    'id': info.get('id', ''),
                    'title': info.get('title', 'Unknown'),
                    'url': url,
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', '')
                }]
    except Exception as e:
        print(f"Error extracting info: {e}")
        return []


def get_video_info(url):
    """Get info for a single video"""
    ffmpeg_path = ensure_ffmpeg()
    opts = get_ydl_opts(ffmpeg_path)
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info:
                return {
                    'id': info.get('id', ''),
                    'title': info.get('title', 'Unknown'),
                    'url': url,
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail', '')
                }
    except Exception as e:
        print(f"Error getting video info: {e}")
    return None


def download_as_mp3(url, video_id, title, output_dir=None):
    """
    Download a video and convert to MP3
    Args:
        url: YouTube video URL
        video_id: Video ID
        title: Video title
        output_dir: Optional custom output directory (Path object or string)
    Returns the path to the downloaded file or None on failure
    """
    ffmpeg_path = ensure_ffmpeg()
    if not ffmpeg_path:
        return None
    
    # Use provided output_dir or default
    if output_dir is None:
        output_dir = DOWNLOADS_DIR
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    if not safe_title:
        safe_title = video_id
    
    output_path = output_dir / f"{safe_title}.mp3"
    
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': str(Path(ffmpeg_path).parent),
        'outtmpl': str(output_dir / f"{safe_title}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        
        if output_path.exists():
            return str(output_path)
    except Exception as e:
        print(f"Error downloading {title}: {e}")
    
    return None


def format_duration(seconds):
    """Format duration in seconds to MM:SS"""
    if not seconds:
        return "Unknown"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes}:{secs:02d}"


def download_media(url, video_id, title, output_dir=None, format_type='mp3'):
    """
    Download a video in specified format
    
    Args:
        url: YouTube video URL
        video_id: Video ID
        title: Video title
        output_dir: Output directory (Path or string)
        format_type: 'mp3', 'mp4', 'mp4_1080', or 'm4a'
    
    Returns the path to the downloaded file or None on failure
    """
    ffmpeg_path = ensure_ffmpeg()
    if not ffmpeg_path:
        return None
    
    # Use provided output_dir or default
    if output_dir is None:
        output_dir = DOWNLOADS_DIR
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '(', ')')).strip()
    if not safe_title:
        safe_title = video_id
    
    # Configure based on format
    if format_type == 'mp3':
        extension = 'mp3'
        opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    elif format_type == 'mp4':
        extension = 'mp4'
        opts = {
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
            'merge_output_format': 'mp4',
        }
    elif format_type == 'mp4_1080':
        extension = 'mp4'
        opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
            'merge_output_format': 'mp4',
        }
    elif format_type == 'm4a':
        extension = 'm4a'
        opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a',
                'preferredquality': '256',
            }],
        }
    else:
        # Default to mp3
        extension = 'mp3'
        opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    
    output_path = output_dir / f"{safe_title}.{extension}"
    
    # Use android player client to bypass 403 errors (no cookies/admin needed)
    # Maximum speed optimizations
    opts.update({
        'ffmpeg_location': str(Path(ffmpeg_path).parent),
        'outtmpl': str(output_dir / f"{safe_title}.%(ext)s"),
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
        # Speed optimizations - aggressive
        'concurrent_fragment_downloads': 8,  # Download 8 fragments at once (max)
        'buffersize': 1024 * 64,  # 64KB buffer
        'http_chunk_size': 10485760,  # 10MB chunks
        'retries': 1,  # Minimal retries for speed
        'fragment_retries': 1,
        'socket_timeout': 8,  # Shorter timeout
        'noprogress': True,  # Disable progress for speed
        'no_check_certificates': True,  # Skip SSL verification
        'geo_bypass': True,
        # FFmpeg optimization for faster encoding
        'postprocessor_args': {
            'ffmpeg': ['-threads', '0'],  # Use all CPU cores
        },
    })
    
    # Try download (with retries and fallback strategies)
    strategies = [
        ('android client', {'extractor_args': {'youtube': {'player_client': ['android']}}}),
        ('web client', {'extractor_args': {'youtube': {'player_client': ['web']}}}),
        ('default', {}),
    ]
    
    for strategy_name, extra_opts in strategies:
        try:
            print(f"Trying download with {strategy_name}...")
            current_opts = opts.copy()
            current_opts.update(extra_opts)
            
            with yt_dlp.YoutubeDL(current_opts) as ydl:
                ydl.download([url])
            
            # Check if file exists
            if output_path.exists():
                print(f"Downloaded: {output_path}")
                return str(output_path)
            
            # Check for alternative extensions
            for f in output_dir.glob(f"{safe_title}.*"):
                if f.suffix.lower() in ['.mp3', '.mp4', '.m4a', '.webm']:
                    print(f"Downloaded: {f}")
                    return str(f)
                    
        except Exception as e:
            error_msg = str(e)
            print(f"{strategy_name} failed: {error_msg}")
            
            # If it's a 403 error, try next strategy
            if '403' in error_msg:
                continue
            # For other errors, stop trying
            break
    
    print(f"All download strategies failed for: {title}")
    return None

