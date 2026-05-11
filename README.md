# TheTVDB NFO Crawler

A web-based tool for crawling anime metadata from TheTVDB and generating Emby/Jellyfin-compatible NFO files. No API key required.

## Features

- **Web UI** - Intuitive browser interface with real-time search and crawl progress
- **CLI Mode** - Command-line usage for scripting and automation
- **Language Priority** - Drag-and-drop language ordering (Traditional Chinese, Simplified Chinese, Japanese, English) for picking the best translation
- **Full Metadata** - Series overview, actors, directors, writers, genres, ratings, artwork
- **Artwork Download** - Posters, fanart, clearlogos, banners, season posters, and episode thumbnails
- **NFO Generation** - `tvshow.nfo`, `season.nfo`, and per-episode NFO files ready for your media server
- **No API Key** - Pure web scraping approach, no registration needed

## Screenshots

### Homepage
![Homepage](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/001-homepage.png)

### Search Results
![Search Results](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/002-search-results.png)

### Emby / Jellyfin Output Structure
![Emby Output](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/003-emby-output.png)

### Season Content & Episode NFO Files
![Season Structure](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/004-season-structure.png)

## Installation

```bash
git clone https://github.com/acer1204/TheTVDB-NFO-Crawler.git
cd TheTVDB-NFO-Crawler
pip install -r requirements.txt
```

## Usage

### Web UI

Launch the web server:

```bash
python server.py
```

Or on Windows, double-click `tvdb_crawler.bat` and enter `web`.

Then open `http://localhost:5000` in your browser.

### CLI Mode

```bash
# Search by name
python tvdb_crawler.py "一騎当千"

# Search and specify output directory
python tvdb_crawler.py "一騎当千" -o ./output

# Direct URL
python tvdb_crawler.py -u "https://www.thetvdb.com/series/ikki-tousen"

# Direct TVDB ID
python tvdb_crawler.py -i 80158

# Generate tvshow.nfo only (skip episodes)
python tvdb_crawler.py "一騎当千" --no-episodes
```

On Windows, you can also run:

```bat
tvdb_crawler.bat "一騎当千"
tvdb_crawler.bat web
```

### Input Methods

1. **Anime name** - Search by title (supports Chinese, Japanese, English)
2. **TVDB URL** - Paste the full series URL from TheTVDB
3. **TVDB ID** - Enter the numeric series ID directly

### Language Priority

Drag the language pills in the web UI to set your preferred translation order. The crawler will pick the first available translation based on your priority list:

| Code | Language        |
|------|-----------------|
| zhtw | 繁體中文         |
| zho  | 簡體中文         |
| jpn  | 日文             |
| eng  | 英文             |

## Output Structure

```
output/<TaskID>/<SeriesName>/
├── tvshow.nfo
├── poster.jpg
├── fanart.jpg
├── banner.jpg
├── clearlogo.png
├── Season 1/
│   ├── season.nfo
│   ├── season01-poster.jpg
│   ├── S01E01.nfo
│   ├── S01E01-thumb.jpg
│   ├── S01E02.nfo
│   ├── S01E02-thumb.jpg
│   └── ...
├── Season 2/
│   └── ...
└── Specials/
    └── ...
```

The generated NFO files contain full metadata including plot overviews, cast details, air dates, external IDs (IMDb, TMDb, TVDB), genres, ratings, and artwork paths compatible with Jellyfin, Emby, and Kodi.

## Dependencies

- Python 3.9+
- Flask (web server)
- requests (HTTP client)
- BeautifulSoup4 / html5lib (HTML parsing)
- lxml (XML/XML generation)

Install all dependencies with:

```bash
pip install -r requirements.txt
```

## Disclaimer

This tool scrapes publicly available data from TheTVDB. Please use responsibly and respect their terms of service. This project is for personal use only.

## Author

**acer1204**

## License

MIT License

---

# TheTVDB NFO Crawler (繁體中文說明)

一個從 TheTVDB 爬取動漫元數據並產生 Emby/Jellyfin 相容 NFO 檔案的網頁工具，不需要 API Key。

## 功能特色

- **網頁介面** - 直觀的瀏覽器操作介面，具備即時搜尋與爬取進度顯示
- **命令列模式** - 支援指令稿與自動化操作
- **語系優先排序** - 可拖曳調整語系優先順序（繁體中文、簡體中文、日文、英文），自動挑選最佳翻譯
- **完整元數據** - 系列概述、演員、導演、編劇、類型、評分、圖片
- **圖片下載** - 海報、粉絲藝術、透明標誌、橫幅、季別海報與各集縮圖
- **NFO 產生** - 自動產生 `tvshow.nfo`、`season.nfo` 及各集 NFO 檔案
- **不需 API Key** - 純網頁爬蟲方式，不需註冊

## 預覽截圖

### 首頁
![首頁](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/001-homepage.png)

### 搜尋結果
![搜尋結果](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/002-search-results.png)

### Emby / Jellyfin 輸出結構
![Emby 輸出](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/003-emby-output.png)

### 季內容與各集 NFO 檔案
![季內容結構](https://raw.githubusercontent.com/acer1204/TheTVDB-NFO-Crawler/main/screenshots/004-season-structure.png)

## 安裝

```bash
git clone https://github.com/acer1204/TheTVDB-NFO-Crawler.git
cd TheTVDB-NFO-Crawler
pip install -r requirements.txt
```

## 使用方式

### 網頁介面

啟動網頁伺服器：

```bash
python server.py
```

或在 Windows 上雙擊 `tvdb_crawler.bat` 並輸入 `web`。

然後在瀏覽器中開啟 `http://localhost:5000`。

### 命令列模式

```bash
# 依名稱搜尋
python tvdb_crawler.py "一騎当千"

# 搜尋並指定輸出目錄
python tvdb_crawler.py "一騎当千" -o ./output

# 直接給定 TVDB 網址
python tvdb_crawler.py -u "https://www.thetvdb.com/series/ikki-tousen"

# 直接給定 TVDB ID
python tvdb_crawler.py -i 80158

# 只產生 tvshow.nfo（略過各集）
python tvdb_crawler.py "一騎当千" --no-episodes
```

Windows 上也可執行：

```bat
tvdb_crawler.bat "一騎当千"
tvdb_crawler.bat web
```

### 輸入方式

1. **動漫名稱** - 透過名稱搜尋（支援中文、日文、英文）
2. **TVDB 網址** - 直接貼上 TheTVDB 的系列網址
3. **TVDB ID** - 直接輸入數字系列的 ID

### 語系優先排序

在網頁介面中拖曳語言膠囊來設定翻譯優先順序。爬蟲會依據你的優先順序挑選第一個可用的翻譯：

| 代碼   | 語言         |
|--------|-------------|
| zhtw   | 繁體中文     |
| zho    | 簡體中文     |
| jpn    | 日文         |
| eng    | 英文         |

## 輸出結構

```
output/<TaskID>/<SeriesName>/
├── tvshow.nfo
├── poster.jpg
├── fanart.jpg
├── banner.jpg
├── clearlogo.png
├── Season 1/
│   ├── season.nfo
│   ├── season01-poster.jpg
│   ├── S01E01.nfo
│   ├── S01E01-thumb.jpg
│   ├── S01E02.nfo
│   ├── S01E02-thumb.jpg
│   └── ...
├── Season 2/
│   └── ...
└── Specials/
    └── ...
```

產生的 NFO 檔案包含完整的元數據資訊，包括劇情概述、演員詳情、播出日期、外部 ID（IMDb、TMDb、TVDB）、類型、評分與圖片路徑，與 Jellyfin、Emby、Kodi 相容。

## 依賴套件

- Python 3.9+
- Flask（網頁伺服器）
- requests（HTTP 客戶端）
- BeautifulSoup4 / html5lib（HTML 解析）
- lxml（XML 生成）

安裝所有依賴套件：

```bash
pip install -r requirements.txt
```

## 免責聲明

本工具爬取 TheTVDB 上的公開資料。請合理使用並遵守其服務條款。本專案僅供個人使用。

## 作者

**acer1204**

## 授權

MIT License
