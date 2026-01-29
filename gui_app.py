"""
YouTube to MP3/MP4 Converter - GUI Version
Using CustomTkinter for modern UI
"""
import os
import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path

from utils.downloader import extract_playlist_info, download_media, format_duration, ensure_ffmpeg
from utils.similarity import find_duplicates_smart

# App settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VideoItem(ctk.CTkFrame):
    """A single video item with checkbox"""
    def __init__(self, master, video, index, is_duplicate=False, group_id=None, **kwargs):
        super().__init__(master, **kwargs)
        self.video = video
        self.index = index
        
        self.configure(fg_color="#2b2b2b", corner_radius=8)
        
        # Checkbox
        self.var = ctk.BooleanVar(value=True)
        self.checkbox = ctk.CTkCheckBox(
            self, 
            text="",
            variable=self.var,
            width=24,
            checkbox_width=20,
            checkbox_height=20
        )
        self.checkbox.pack(side="left", padx=(10, 5), pady=8)
        
        # Video info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        
        title_text = video.get('title', 'Unknown')
        self.title_label = ctk.CTkLabel(
            info_frame, 
            text=title_text[:60] + "..." if len(title_text) > 60 else title_text,
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.title_label.pack(anchor="w")
        
        duration = video.get('duration_formatted', format_duration(video.get('duration', 0)))
        self.duration_label = ctk.CTkLabel(
            info_frame,
            text=duration,
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.duration_label.pack(anchor="w")
        
        # Duplicate warning
        if is_duplicate:
            self.configure(border_width=2, border_color="#ffa502")
            warning_label = ctk.CTkLabel(
                self,
                text=f"⚠️ 群組 {group_id}",
                font=ctk.CTkFont(size=11),
                text_color="#ffa502"
            )
            warning_label.pack(side="right", padx=10)


class App(ctk.CTk):
    """Main Application"""
    def __init__(self):
        super().__init__()
        
        self.title("YouTube to MP3/MP4 Converter")
        self.geometry("900x850")
        self.minsize(800, 700)
        
        # State
        self.videos = []
        self.video_items = []
        self.download_path = ""
        self.is_downloading = False
        self.is_analyzing = False
        self.animation_value = 0
        
        self.create_widgets()
        
        # Ensure ffmpeg on startup
        threading.Thread(target=self._ensure_ffmpeg, daemon=True).start()
    
    def _ensure_ffmpeg(self):
        """Ensure ffmpeg is available"""
        try:
            ensure_ffmpeg()
        except Exception as e:
            self.after(0, lambda: messagebox.showwarning("FFmpeg", f"FFmpeg 設置失敗: {e}"))
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="🎵 YouTube to MP3/MP4",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Settings Frame
        settings_frame = ctk.CTkFrame(main_frame)
        settings_frame.pack(fill="x", pady=(0, 15))
        
        # Download Path
        path_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        path_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(path_frame, text="📁 下載位置:", font=ctk.CTkFont(size=13)).pack(side="left")
        
        self.path_entry = ctk.CTkEntry(path_frame, width=350, placeholder_text="點擊右邊按鈕選擇...")
        self.path_entry.pack(side="left", padx=10)
        
        self.browse_btn = ctk.CTkButton(
            path_frame, 
            text="瀏覽", 
            width=80,
            command=self.browse_folder
        )
        self.browse_btn.pack(side="left")
        
        # Format Selection
        format_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(format_frame, text="🎵 格式:", font=ctk.CTkFont(size=13)).pack(side="left")
        
        self.format_var = ctk.StringVar(value="mp3")
        formats = [("MP3", "mp3"), ("MP4 720p", "mp4"), ("MP4 1080p", "mp4_1080"), ("M4A", "m4a")]
        
        for text, value in formats:
            rb = ctk.CTkRadioButton(
                format_frame,
                text=text,
                variable=self.format_var,
                value=value
            )
            rb.pack(side="left", padx=10)
        
        # URL Input
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            url_frame, 
            text="輸入 YouTube URL（支援播放清單）",
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.url_textbox = ctk.CTkTextbox(url_frame, height=80)
        self.url_textbox.pack(fill="x", padx=15, pady=(0, 10))
        
        self.analyze_btn = ctk.CTkButton(
            url_frame,
            text="🔍 分析 URL",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            command=self.analyze_urls
        )
        self.analyze_btn.pack(padx=15, pady=(0, 10))
        
        # Video List
        list_frame = ctk.CTkFrame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Header
        header_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=10)
        
        self.count_label = ctk.CTkLabel(
            header_frame,
            text="🎶 歌曲列表 (0 首)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.count_label.pack(side="left")
        
        ctk.CTkButton(
            header_frame, text="全選", width=60,
            command=lambda: self.set_all_checkboxes(True)
        ).pack(side="right", padx=2)
        
        ctk.CTkButton(
            header_frame, text="取消全選", width=80,
            command=lambda: self.set_all_checkboxes(False)
        ).pack(side="right", padx=2)
        
        # Scrollable video list
        self.video_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        self.video_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Download Button
        self.download_btn = ctk.CTkButton(
            main_frame,
            text="⬇️ 下載選取的歌曲",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#ff4757",
            hover_color="#ff6b7a",
            command=self.start_download,
            state="disabled"
        )
        self.download_btn.pack(fill="x")
        
        # Progress
        self.progress_frame = ctk.CTkFrame(main_frame)
        
        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="準備中...",
            font=ctk.CTkFont(size=12)
        )
        self.progress_label.pack(pady=(10, 5))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=400)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.set(0)
    
    def browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory(title="選擇下載資料夾")
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.download_path = folder
    
    def parse_urls(self, text):
        """Parse URLs from text"""
        lines = text.strip().split('\n')
        urls = []
        for line in lines:
            line = line.strip()
            if line and ('youtube.com' in line or 'youtu.be' in line):
                urls.append(line)
        return urls
    
    def analyze_urls(self):
        """Analyze YouTube URLs"""
        text = self.url_textbox.get("1.0", "end")
        urls = self.parse_urls(text)
        
        if not urls:
            messagebox.showwarning("警告", "請輸入至少一個 YouTube URL")
            return
        
        # Detect Mix playlist (RD... in list parameter)
        is_mix = any('list=RD' in url for url in urls)
        
        # If Mix detected, ask for limit
        limit = None
        if is_mix:
            dialog = ctk.CTkInputDialog(
                text="偵測到 Mix (合集/電台)，可能包含數千首歌曲。\n請輸入要載入的歌曲數量 (建議 50-100):",
                title="Mix 播放清單限制"
            )
            limit_str = dialog.get_input()
            
            if limit_str is None:
                return  # User cancelled
            
            try:
                limit = int(limit_str) if limit_str else 50
                limit = max(1, min(limit, 500))  # Clamp between 1-500
            except ValueError:
                limit = 50
        
        # Show analyzing progress
        self.analyze_btn.configure(state="disabled", text="⏳ 分析中...")
        self.progress_frame.pack(fill="x", pady=(15, 0))
        self.progress_label.configure(text="正在連接 YouTube，請稍候...")
        
        # Start manual animation
        self.is_analyzing = True
        self.animation_value = 0
        self._animate_progress()
        
        threading.Thread(target=self._analyze_urls_thread, args=(urls, limit), daemon=True).start()
    
    def _animate_progress(self):
        """Animate progress bar manually"""
        if not self.is_analyzing:
            return
        
        # Bounce animation (0 -> 1 -> 0)
        self.animation_value += 0.05
        if self.animation_value > 1:
            self.animation_value = 0
        
        self.progress_bar.set(self.animation_value)
        self.after(50, self._animate_progress)  # Update every 50ms
    
    def _analyze_urls_thread(self, urls, limit=None):
        """Analyze URLs in background thread"""
        all_videos = []
        
        for i, url in enumerate(urls):
            self.after(0, lambda i=i, n=len(urls): self.progress_label.configure(
                text=f"分析中 ({i+1}/{n})，請稍候..."
            ))
            try:
                videos = extract_playlist_info(url)
                if videos:
                    # Apply limit if specified
                    if limit and len(all_videos) + len(videos) > limit:
                        remaining = limit - len(all_videos)
                        videos = videos[:remaining]
                    
                    # Update status with count so far
                    self.after(0, lambda c=len(videos): self.progress_label.configure(
                        text=f"已找到 {len(all_videos) + c} 首歌曲，載入中..."
                    ))
                    for v in videos:
                        v['duration_formatted'] = format_duration(v.get('duration', 0))
                    all_videos.extend(videos)
                    
                    # Stop if limit reached
                    if limit and len(all_videos) >= limit:
                        break
            except Exception as e:
                print(f"Error: {e}")
        
        # Processing duplicates
        self.after(0, lambda: self.progress_label.configure(text=f"處理 {len(all_videos)} 首歌曲..."))
        
        self.after(0, lambda: self._update_video_list(all_videos))
    
    def _update_video_list(self, videos):
        """Update the video list UI"""
        # Stop the progress animation
        self.is_analyzing = False
        self.progress_bar.set(0)
        self.progress_frame.pack_forget()
        
        self.videos = videos
        self.video_items = []
        
        # Clear existing items
        for widget in self.video_scroll.winfo_children():
            widget.destroy()
        
        if not videos:
            messagebox.showinfo("結果", "未找到任何影片")
            self.analyze_btn.configure(state="normal", text="🔍 分析 URL")
            return
        
        # Check duplicates with improved algorithm
        duplicate_groups, duplicate_indices = find_duplicates_smart(videos, threshold=85)
        
        # Create video items
        for i, video in enumerate(videos):
            is_dup = i in duplicate_indices
            group_id = None
            if is_dup:
                for g_idx, group in enumerate(duplicate_groups):
                    if i in group:
                        group_id = g_idx + 1
                        break
            
            item = VideoItem(
                self.video_scroll,
                video,
                i,
                is_duplicate=is_dup,
                group_id=group_id
            )
            item.pack(fill="x", pady=2)
            self.video_items.append(item)
        
        self.count_label.configure(text=f"🎶 歌曲列表 ({len(videos)} 首)")
        self.analyze_btn.configure(state="normal", text="🔍 分析 URL")
        self.download_btn.configure(state="normal")
    
    def set_all_checkboxes(self, checked):
        """Set all checkboxes"""
        for item in self.video_items:
            item.var.set(checked)
    
    def get_selected_videos(self):
        """Get list of selected videos"""
        selected = []
        for item in self.video_items:
            if item.var.get():
                selected.append(item.video)
        return selected
    
    def start_download(self):
        """Start downloading selected videos"""
        selected = self.get_selected_videos()
        
        if not selected:
            messagebox.showwarning("警告", "請至少選擇一首歌曲")
            return
        
        # Get download path
        download_path = self.path_entry.get().strip()
        if not download_path:
            download_path = str(Path(__file__).parent / "downloads")
        
        self.download_path = download_path
        
        # Show progress
        self.progress_frame.pack(fill="x", pady=(15, 0))
        self.download_btn.configure(state="disabled")
        self.is_downloading = True
        
        # Start download thread
        output_format = self.format_var.get()
        threading.Thread(
            target=self._download_thread,
            args=(selected, download_path, output_format),
            daemon=True
        ).start()
    
    def _download_thread(self, videos, download_path, output_format):
        """Download videos in background"""
        import time
        import random
        
        total = len(videos)
        success = 0
        failed = 0
        
        # Create directory
        Path(download_path).mkdir(parents=True, exist_ok=True)
        
        for i, video in enumerate(videos):
            # Shorter delay between downloads (0.3-0.8s) for faster batch downloads
            if i > 0:
                time.sleep(random.uniform(0.3, 0.8))
            
            self.after(0, lambda i=i, t=total: self._update_progress(i, t, video.get('title', '')))
            
            try:
                path = download_media(
                    video.get('url', ''),
                    video.get('id', ''),
                    video.get('title', 'Unknown'),
                    download_path,
                    output_format
                )
                if path:
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Download error: {e}")
                failed += 1
        
        self.after(0, lambda: self._download_complete(success, failed, total))
    
    def _update_progress(self, current, total, title):
        """Update progress bar"""
        progress = (current + 1) / total
        self.progress_bar.set(progress)
        short_title = title[:40] + "..." if len(title) > 40 else title
        self.progress_label.configure(text=f"下載中 ({current + 1}/{total}): {short_title}")
    
    def _download_complete(self, success, failed, total):
        """Called when download is complete"""
        self.progress_bar.set(1)
        self.progress_label.configure(text=f"完成! {success}/{total} 個檔案下載成功")
        self.download_btn.configure(state="normal")
        self.is_downloading = False
        
        # Show result
        msg = f"下載完成!\n\n成功: {success} 個\n失敗: {failed} 個\n\n儲存位置:\n{self.download_path}"
        messagebox.showinfo("完成", msg)
        
        # Open folder
        if success > 0:
            os.startfile(self.download_path)


if __name__ == "__main__":
    app = App()
    app.mainloop()
