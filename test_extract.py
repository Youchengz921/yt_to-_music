"""Test script for URL extraction"""
from utils.downloader import extract_playlist_info

url = "https://www.youtube.com/watch?v=T6bIz_8AWq0&list=RDT6bIz_8AWq0"
print(f"Testing URL: {url}")
print("Extracting...")

videos = extract_playlist_info(url)
print(f"Found {len(videos)} videos")

for i, v in enumerate(videos[:10]):
    print(f"  {i+1}. {v['title']}")
