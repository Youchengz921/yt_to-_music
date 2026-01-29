"""
FFmpeg downloader utility
Automatically downloads and extracts ffmpeg for Windows
"""
import os
import sys
import zipfile
import requests
from pathlib import Path

FFMPEG_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
FFMPEG_DIR = Path(__file__).parent.parent / "ffmpeg"


def get_ffmpeg_path():
    """Get the path to ffmpeg executable"""
    ffmpeg_exe = FFMPEG_DIR / "bin" / "ffmpeg.exe"
    if ffmpeg_exe.exists():
        return str(ffmpeg_exe)
    return None


def download_ffmpeg():
    """Download and extract ffmpeg if not present"""
    ffmpeg_exe = FFMPEG_DIR / "bin" / "ffmpeg.exe"
    
    if ffmpeg_exe.exists():
        print("✓ FFmpeg already installed")
        return str(ffmpeg_exe)
    
    print("Downloading FFmpeg...")
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    
    zip_path = FFMPEG_DIR / "ffmpeg.zip"
    
    # Download with progress
    response = requests.get(FFMPEG_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(zip_path, 'wb') as f:
        downloaded = 0
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                percent = (downloaded / total_size) * 100
                print(f"\rDownloading: {percent:.1f}%", end="", flush=True)
    
    print("\nExtracting FFmpeg...")
    
    # Extract
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(FFMPEG_DIR)
    
    # Move files from nested folder to ffmpeg/bin
    extracted_folders = [d for d in FFMPEG_DIR.iterdir() if d.is_dir() and d.name.startswith("ffmpeg")]
    if extracted_folders:
        extracted_bin = extracted_folders[0] / "bin"
        target_bin = FFMPEG_DIR / "bin"
        target_bin.mkdir(exist_ok=True)
        
        for file in extracted_bin.iterdir():
            target = target_bin / file.name
            if not target.exists():
                file.rename(target)
    
    # Cleanup
    zip_path.unlink()
    
    if ffmpeg_exe.exists():
        print("✓ FFmpeg installed successfully")
        return str(ffmpeg_exe)
    else:
        print("✗ FFmpeg installation failed")
        return None


if __name__ == "__main__":
    download_ffmpeg()
