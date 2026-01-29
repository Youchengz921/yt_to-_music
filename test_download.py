"""Quick test of the new downloader"""
import sys
sys.path.insert(0, 'c:/code/code/yt_to_music')

from utils.downloader import download_media, ensure_ffmpeg

# Test download
url = "https://www.youtube.com/watch?v=ySako_wFPPE"
video_id = "ySako_wFPPE"
title = "Test Song"
output_dir = "C:/Users/mypc/Downloads/mp3"

print("Testing download_media function...")
result = download_media(url, video_id, title, output_dir, 'mp3')

if result:
    print(f"\n✓ SUCCESS! Downloaded to: {result}")
else:
    print("\n✗ FAILED!")
