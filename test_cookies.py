"""
Test script to find a working cookie extraction method
"""
import os
import sys
import tempfile
from pathlib import Path

# Add venv to path
sys.path.insert(0, str(Path(__file__).parent / 'venv' / 'Lib' / 'site-packages'))

def test_download():
    import yt_dlp
    
    url = "https://www.youtube.com/watch?v=ySako_wFPPE"
    output_dir = Path("C:/Users/mypc/Downloads/mp3")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Method 1: Try without cookies first (some videos don't need them)
    print("\n=== Method 1: No cookies ===")
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(output_dir / 'test_method1.%(ext)s'),
        'quiet': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        print("Method 1 SUCCESS!")
        return True
    except Exception as e:
        print(f"Method 1 failed: {e}")
    
    # Method 2: Try with browser_cookie3 (with shadowcopy if available)
    print("\n=== Method 2: browser_cookie3 ===")
    try:
        import browser_cookie3
        
        # Try each browser
        for name, func in [('chrome', browser_cookie3.chrome), 
                           ('edge', browser_cookie3.edge)]:
            try:
                print(f"Trying {name}...")
                cj = func(domain_name=".youtube.com")
                cookies = list(cj)
                if cookies:
                    print(f"Got {len(cookies)} cookies from {name}")
                    
                    # Write cookies to file
                    fd, cookie_file = tempfile.mkstemp(suffix='.txt', text=True)
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        f.write("# Netscape HTTP Cookie File\n")
                        for cookie in cookies:
                            flag = "TRUE" if cookie.domain.startswith('.') else "FALSE"
                            secure = "TRUE" if cookie.secure else "FALSE"
                            expires = int(cookie.expires) if cookie.expires else 0
                            f.write(f"{cookie.domain}\t{flag}\t{cookie.path}\t{secure}\t{expires}\t{cookie.name}\t{cookie.value}\n")
                    
                    opts['cookiefile'] = cookie_file
                    opts['outtmpl'] = str(output_dir / 'test_method2.%(ext)s')
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        ydl.download([url])
                    print(f"Method 2 SUCCESS with {name}!")
                    os.remove(cookie_file)
                    return True
            except Exception as e:
                print(f"{name} failed: {e}")
                continue
    except ImportError:
        print("browser_cookie3 not available")
    except Exception as e:
        print(f"Method 2 failed: {e}")
    
    # Method 3: Try yt-dlp's native extraction
    print("\n=== Method 3: yt-dlp native cookies ===")
    for browser in ['edge', 'chrome']:
        try:
            print(f"Trying yt-dlp with {browser}...")
            opts.pop('cookiefile', None)
            opts['cookiesfrombrowser'] = (browser,)
            opts['outtmpl'] = str(output_dir / f'test_method3_{browser}.%(ext)s')
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            print(f"Method 3 SUCCESS with {browser}!")
            return True
        except Exception as e:
            print(f"{browser} failed: {e}")
            continue
    
    print("\n=== All methods failed ===")
    return False

if __name__ == "__main__":
    test_download()
