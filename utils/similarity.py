"""
Song title similarity detection
Uses fuzzy matching to find potential duplicate songs
"""
import re
from fuzzywuzzy import fuzz


# Common patterns to remove from titles (expanded for Chinese music)
NOISE_PATTERNS = [
    # English patterns
    r'\(official\s*(music\s*)?video\)',
    r'\(official\s*audio\)',
    r'\(lyric\s*video\)',
    r'\(lyrics?\)',
    r'\(mv\)',
    r'\(audio\)',
    r'\[official\s*(music\s*)?video\]',
    r'\[official\s*audio\]',
    r'\[lyric\s*video\]',
    r'\[lyrics?\]',
    r'\[mv\]',
    r'\[audio\]',
    r'official\s*music\s*video',
    r'official\s*video',
    r'official\s*audio',
    r'lyric\s*video',
    r'\|.*$',  # Everything after |
    r'\d{4}\s*(mv|music\s*video)',  # Year + MV
    r'hd|4k|1080p|720p',
    r'feat\.?\s*[\w\s]+',
    r'ft\.?\s*[\w\s]+',
    r'prod\.?\s*[\w\s]+',
    
    # Chinese patterns (expanded)
    r'【.*?】',   # Chinese square brackets
    r'「.*?」',   # Japanese quotes
    r'『.*?』',   # Japanese double quotes
    r'《.*?》',   # Chinese book title marks (keep for extraction, remove version info)
    r'动态歌词',
    r'動態歌詞',
    r'歌词版?',
    r'歌詞版?',
    r'完整版',
    r'高清版?',
    r'高音質',
    r'高音质',
    r'無損',
    r'无损',
    r'lyrics?',
    r'pinyin',
    r'拼音',
    r'viet\s*sub',
    r'vietsub',
    r'中文字幕',
    r'附詞',
    r'附词',
    r'純音樂',
    r'纯音乐',
    r'伴奏',
    r'cover',
    r'翻唱',
    r'live',
    r'現場',
    r'现场',
    r'演唱會',
    r'演唱会',
]



def normalize_title(title):
    """
    Normalize a song title by removing common noise
    Returns a cleaned, lowercase version of the title
    """
    if not title:
        return ""
    
    normalized = title.lower().strip()
    
    # Apply all noise patterns
    for pattern in NOISE_PATTERNS:
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Remove leading/trailing punctuation
    normalized = re.sub(r'^[\s\-\|:]+|[\s\-\|:]+$', '', normalized)
    
    return normalized


def calculate_similarity(title1, title2):
    """
    Calculate similarity between two titles
    Returns a score from 0-100
    """
    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)
    
    if not norm1 or not norm2:
        return 0
    
    # Use token set ratio for better matching with word order differences
    return fuzz.token_set_ratio(norm1, norm2)


def find_duplicates(videos, threshold=80):
    """
    Find groups of potentially duplicate songs
    
    Args:
        videos: List of video dicts with 'id', 'title', etc.
        threshold: Similarity threshold (0-100)
    
    Returns:
        List of duplicate groups, each group is a list of video indices
        Also returns a set of indices that are part of some duplicate group
    """
    n = len(videos)
    duplicate_pairs = []
    
    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            similarity = calculate_similarity(videos[i]['title'], videos[j]['title'])
            if similarity >= threshold:
                duplicate_pairs.append((i, j, similarity))
    
    # Build groups using union-find approach
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for i, j, _ in duplicate_pairs:
        union(i, j)
    
    # Collect groups
    groups = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)
    
    # Only return groups with more than 1 member
    duplicate_groups = [indices for indices in groups.values() if len(indices) > 1]
    
    # Get set of all indices in duplicate groups
    duplicate_indices = set()
    for group in duplicate_groups:
        duplicate_indices.update(group)
    
    return duplicate_groups, duplicate_indices


def extract_song_name(title):
    """
    Extract the actual song name from a title by removing artist names
    Common patterns:
    - Artist - Song Name
    - Artist | Song Name
    - Artist《Song Name》
    - Artist「Song Name」
    """
    if not title:
        return ""
    
    # Try to extract from Chinese brackets first
    match = re.search(r'[《「【](.+?)[》」】]', title)
    if match:
        return match.group(1).strip()
    
    # Try separator patterns
    separators = [' - ', ' | ', ' – ', '：', ': ']
    for sep in separators:
        if sep in title:
            parts = title.split(sep, 1)
            if len(parts) == 2:
                # Return the longer part (usually the song name)
                return parts[1].strip()
    
    return title


def find_duplicates_smart(videos, threshold=85):
    """
    Improved duplicate detection that focuses on song names, not artist names
    
    Args:
        videos: List of video dicts with 'id', 'title', etc.
        threshold: Similarity threshold (0-100)
    
    Returns:
        List of duplicate groups, each group is a list of video indices
        Also returns a set of indices that are part of some duplicate group
    """
    n = len(videos)
    duplicate_pairs = []
    
    # Compare all pairs using extracted song names
    for i in range(n):
        song1 = extract_song_name(videos[i]['title'])
        norm1 = normalize_title(song1)
        
        for j in range(i + 1, n):
            song2 = extract_song_name(videos[j]['title'])
            norm2 = normalize_title(song2)
            
            if not norm1 or not norm2:
                continue
                
            # Only mark as duplicate if song names are very similar
            similarity = fuzz.token_set_ratio(norm1, norm2)
            if similarity >= threshold:
                duplicate_pairs.append((i, j, similarity))
    
    # Build groups using union-find approach
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    for i, j, _ in duplicate_pairs:
        union(i, j)
    
    # Collect groups
    groups = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)
    
    # Only return groups with more than 1 member
    duplicate_groups = [indices for indices in groups.values() if len(indices) > 1]
    
    # Get set of all indices in duplicate groups
    duplicate_indices = set()
    for group in duplicate_groups:
        duplicate_indices.update(group)
    
    return duplicate_groups, duplicate_indices

