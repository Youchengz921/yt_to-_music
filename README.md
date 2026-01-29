# YouTube to MP3/MP4 Converter

一個簡單易用的 YouTube 影片/播放清單下載工具，支援轉換為 MP3、MP4、M4A 格式。

## ✨ 功能特點

- **🎵 多種格式支援** - MP3、MP4 (720p/1080p)、M4A
- **📋 播放清單支援** - 一次下載整個播放清單
- **🎛️ Mix 合輯限制** - 偵測 Mix 電台後可選擇下載數量（避免下載太多）
- **🔍 重複偵測** - 智慧檢測相似歌曲，避免重複下載
- **🌐 兩種介面** - Web 版本 + 桌面 GUI 版本
- **📁 自訂下載路徑** - 可選擇任意資料夾存放檔案
- **⚡ 無需登入** - 不需要 YouTube 帳號、不需要管理員權限
- **📱 手機下載** - Web 版可直接下載到手機
- **📦 批次打包** - 支援 ZIP 打包下載

## 📋 系統需求

- Python 3.8+
- Windows 10/11

## 🚀 安裝步驟

1. **建立虛擬環境**
```powershell
cd yt_to_music
python -m venv venv
.\venv\Scripts\activate
```

2. **安裝依賴**
```powershell
pip install -r requirements.txt
pip install customtkinter  # GUI 版本需要
```

3. **更新 yt-dlp（建議）**
```powershell
pip install yt-dlp -U --pre
```

## 📖 使用方式

### Web 版本（推薦）
```powershell
python app.py
```
然後打開瀏覽器訪問 `http://localhost:5000`

### GUI 桌面版本
```powershell
python gui_app.py
```

## 🎯 使用流程

1. **貼上 YouTube 網址** - 支援單一影片或播放清單
2. **點擊「分析」** - 系統會解析影片資訊
3. **選擇要下載的影片** - 可全選或個別勾選
4. **選擇輸出格式** - MP3/MP4/M4A
5. **選擇儲存位置** - 點擊「瀏覽」選擇資料夾
6. **開始下載** - 點擊「下載」按鈕

## 📁 專案結構

```
yt_to_music/
├── app.py              # Flask Web 應用程式
├── gui_app.py          # CustomTkinter GUI 應用程式
├── requirements.txt    # Python 依賴
├── utils/
│   ├── downloader.py   # 下載核心邏輯
│   ├── similarity.py   # 重複偵測演算法
│   └── ffmpeg_setup.py # FFmpeg 自動設定
├── static/             # Web 靜態資源
│   ├── css/
│   └── js/
└── templates/          # HTML 模板
    └── index.html
```

## ⚠️ 注意事項

- FFmpeg 會在首次執行時自動下載
- 部分有版權保護的影片可能無法下載
- 請遵守 YouTube 的服務條款

## 🛠️ 技術實現

- **yt-dlp** - YouTube 影片下載引擎
- **FFmpeg** - 音視頻轉換
- **Flask** - Web 框架
- **CustomTkinter** - 現代化 GUI 框架
- **FuzzyWuzzy** - 字串相似度比對（用於重複偵測）

## 📄 License

MIT License
