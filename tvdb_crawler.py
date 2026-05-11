#!/usr/bin/env python3
"""
TheTVDB NFO Crawler (純爬蟲版，不需 API Key)
從 TheTVDB 網站直接爬取動漫資訊，產生 Emby/Jellyfin 相容的 NFO 檔案

使用方式:
    py tvdb_crawler.py "一騎当千"              # 搜尋並輸出 NFO
    py tvdb_crawler.py -u "https://..."        # 直接給 TVDB 網址
    py tvdb_crawler.py -i 80158                # 直接用 TVDB ID
    py tvdb_crawler.py "名稱" -o ./output      # 指定輸出目錄
"""

import sys
import io
import re
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from lxml import etree

BASE_URL = "https://www.thetvdb.com"
LEGACY_API = "https://thetvdb.com/api"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,ja;q=0.7",
})


def http_get(url, **kw):
    resp = SESSION.get(url, timeout=30, **kw)
    resp.raise_for_status()
    return resp


ARTWORK_BASE = "https://artworks.thetvdb.com"

LANG_GROUPS = {
    "zhtw": ["zhtw", "zh-Hant"],
    "zho":  ["zho", "zhs", "zhcn", "zh-Hans"],
    "jpn":  ["jpn"],
    "eng":  ["eng"],
}
DEFAULT_PRIORITY = ["zhtw", "zho", "jpn", "eng"]


def download_image(url, filepath, timeout=30):
    if not url:
        return False
    try:
        resp = SESSION.get(url, timeout=timeout)
        resp.raise_for_status()
        filepath.write_bytes(resp.content)
        return True
    except Exception:
        return False


def scrape_series_images(soup, series_id):
    result = {"poster": "", "fanart": "", "clearlogo": "", "banner": ""}
    poster_img = soup.select_one("img.img-responsive")
    if poster_img:
        src = poster_img.get("src", "")
        if "artworks" in src:
            result["poster"] = src
    if not result["poster"]:
        result["poster"] = f"{ARTWORK_BASE}/banners/posters/{series_id}-2.jpg"
    for num in range(1, 5):
        url = f"{ARTWORK_BASE}/banners/fanart/original/{series_id}-{num}.jpg"
        try:
            r = SESSION.head(url, timeout=5)
            if r.status_code == 200:
                result["fanart"] = url
                break
        except Exception:
            pass
    for a in soup.select('a[href*="artworks.thetvdb.com"]'):
        href = a.get("href", "")
        if "clearlogo" in href and not result["clearlogo"]:
            result["clearlogo"] = href
        elif "graphical" in href and not result["banner"]:
            result["banner"] = href
        elif "fanart" in href and not result["fanart"]:
            result["fanart"] = href
        elif "poster" in href and not result["poster"]:
            result["poster"] = href
    if not result["banner"]:
        result["banner"] = f"{ARTWORK_BASE}/banners/graphical/{series_id}-g.jpg"
    return result


def scrape_season_images(season_url, series_id, season_num):
    result = {"poster": f"{ARTWORK_BASE}/banners/seasons/{series_id}-{season_num}.jpg"}
    try:
        resp = http_get(season_url)
        soup = BeautifulSoup(resp.text, "html5lib")
        for a in soup.select('a[href*="artworks.thetvdb.com"]'):
            href = a.get("href", "")
            if ("season" in href.lower() or "seasons" in href) and ("poster" in href.lower() or href.endswith(".jpg")):
                result["poster"] = href
                break
    except Exception:
        pass
    return result


def get_episode_image_url(series_id, episode_id):
    return f"{ARTWORK_BASE}/banners/episodes/{series_id}/{episode_id}.jpg"


def search_series(name, lang="zh"):
    resp = http_get(f"{LEGACY_API}/GetSeries.php", params={"seriesname": name, "language": lang})
    root = etree.fromstring(resp.content)
    results = []
    for se in root.findall("Series"):
        results.append({
            "id": (se.findtext("seriesid") or ""),
            "name": (se.findtext("SeriesName") or ""),
            "overview": (se.findtext("Overview") or ""),
            "firstAired": (se.findtext("FirstAired") or ""),
            "aliases": [a.strip() for a in (se.findtext("AliasNames") or "").split("|") if a.strip()],
        })
    return results


def resolve_slug(series_id):
    resp = SESSION.get(f"{BASE_URL}/", params={"tab": "series", "id": series_id},
                       allow_redirects=False, timeout=15)
    loc = resp.headers.get("Location", "")
    if "/series/" in loc:
        return loc.split("/series/")[-1].split("?")[0].split("#")[0]
    return None


def scrape_series_page(slug):
    url = f"{BASE_URL}/series/{slug}"
    resp = http_get(url)
    soup = BeautifulSoup(resp.text, "html5lib")
    data = {"slug": slug, "url": url}

    data["title"] = ""
    h1 = soup.select_one("h1.translated_title, h1#series_title")
    if h1:
        data["title"] = h1.text.strip()

    data.update({
        "series_id": "", "status": "", "first_aired": "", "network": "",
        "runtime": "", "genres": [], "country": "", "language": "",
        "imdb_id": "", "tmdb_id": "",
    })

    info_block = soup.find(id="series_basic_info")
    if info_block:
        for li in info_block.select("li.list-group-item"):
            strong = li.find("strong")
            if not strong:
                continue
            label = strong.text.strip().rstrip(":")
            span = li.find("span")
            value = span.get_text(" ", strip=True) if span else ""
            if "Series ID" in label:
                data["series_id"] = re.sub(r"\D", "", value)
            elif "Status" in label:
                data["status"] = value
            elif "First Aired" in label:
                data["first_aired"] = value
            elif "Network" in label:
                net_span = li.select_one("span a")
                data["network"] = net_span.text.strip() if net_span else value
            elif "Average Runtime" in label:
                nums = re.findall(r"\d+", value)
                data["runtime"] = nums[0] if nums else ""
            elif "Genres" in label:
                data["genres"] = [a.text.strip() for a in li.select("a") if a.text.strip()]
            elif "Original Country" in label:
                data["country"] = value
            elif "Original Language" in label:
                data["language"] = value

    # External IDs from links
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "imdb.com/title/" in href and not data["imdb_id"]:
            m = re.search(r"(tt\d+)", href)
            if m:
                data["imdb_id"] = m.group(1)
        if "themoviedb.org" in href and not data["tmdb_id"]:
            m = re.search(r"/(?:tv|movie)/(\d+)", href)
            if m:
                data["tmdb_id"] = m.group(1)

    # Overviews / title translations
    data["overviews"] = {}
    data["title_translations"] = {}
    for div in soup.select(".change_translation_text"):
        lang = div.get("data-language", "")
        tr_title = div.get("data-title", "")
        p = div.find("p")
        if p and p.text.strip():
            data["overviews"][lang] = p.text.strip()
        if tr_title:
            data["title_translations"][lang] = tr_title

    # Content rating
    data["content_ratings"] = []

    # Actors
    data["actors"] = []
    cast_tab = soup.find(id="castcrew")
    if cast_tab:
        for item in cast_tab.select('[class*="col-xs-6"][class*="col-sm-3"]'):
            links = item.select("a")
            if not links:
                continue
            name_el = links[0]
            # Get only direct text (not child span text)
            direct_texts = [s.strip() for s in name_el.find_all(string=True, recursive=False) if s.strip()]
            name = direct_texts[0] if direct_texts else name_el.get_text(strip=True)
            if not name or name in ("Add Person", "Add Character"):
                continue
            full_text = item.get_text(" ", strip=True)
            role = ""
            m = re.search(r"as\s+(.+?)(?:\s*\*\s*needs role-specific image)?$", full_text)
            if m:
                role = m.group(1).strip()
            data["actors"].append({"name": name, "role": role})

    # Seasons
    data["seasons"] = []
    seasons_tab = soup.find(id="seasons-official")
    if seasons_tab:
        for row in seasons_tab.select("tbody tr"):
            cells = row.select("td")
            if len(cells) < 4:
                continue
            link_el = cells[0].find("a")
            season_name = link_el.text.strip() if link_el else cells[0].text.strip()
            ep_count = cells[3].text.strip()
            if season_name in ("All Seasons", "Unassigned Episodes"):
                continue
            if not ep_count.isdigit() or ep_count == "0":
                continue
            season_url = link_el.get("href") if link_el else ""
            season_num = 0
            m = re.search(r"/official/(\d+)", season_url)
            if m:
                season_num = int(m.group(1))
            if "Specials" in season_name or "specials" in season_name.lower() or "special" in season_name.lower():
                season_num = 0

            from_date = cells[1].text.strip() if len(cells) > 1 else ""
            to_date = cells[2].text.strip() if len(cells) > 2 else ""

            data["seasons"].append({
                "number": season_num,
                "name": season_name,
                "from": from_date,
                "to": to_date,
                "episode_count": int(ep_count),
                "url": urljoin(BASE_URL, season_url) if season_url else "",
            })

    # Trailers
    data["trailers"] = []
    for a in soup.select("a[href*='youtube.com'], a[href*='youtu.be']"):
        href = a.get("href", "")
        if href and href not in data["trailers"]:
            data["trailers"].append(href)

    data["tags"] = []
    data["images"] = scrape_series_images(soup, data.get("series_id", ""))
    return data


def scrape_season_page(season_url):
    resp = http_get(season_url)
    soup = BeautifulSoup(resp.text, "html5lib")
    episodes = []
    for table in soup.select("table.table"):
        for row in table.select("tbody tr"):
            cells = row.select("td")
            if len(cells) < 4:
                continue
            link_el = cells[1].find("a") if len(cells) > 1 else None
            ep_title = link_el.text.strip() if link_el else cells[1].text.strip()
            aired = cells[2].text.strip() if len(cells) > 2 else ""
            runtime_str = cells[3].text.strip() if len(cells) > 3 else ""
            ep_link = link_el.get("href") if link_el else ""
            ep_id = ""
            m = re.search(r"/episodes/(\d+)", ep_link)
            if m:
                ep_id = m.group(1)
            ep_code = cells[0].text.strip()
            ep_num = 0
            ep_season = 0
            m2 = re.match(r"S(\d+)E(\d+)", ep_code)
            if m2:
                ep_season = int(m2.group(1))
                ep_num = int(m2.group(2))
            runtime_nums = re.findall(r"\d+", runtime_str)
            ep_runtime = runtime_nums[0] if runtime_nums else ""
            episodes.append({
                "id": ep_id,
                "number": ep_num,
                "seasonNumber": ep_season,
                "name": ep_title,
                "aired": aired,
                "runtime": ep_runtime,
                "url": urljoin(BASE_URL, ep_link) if ep_link else "",
            })
    return episodes


def scrape_episode_page(ep_url):
    resp = http_get(ep_url)
    soup = BeautifulSoup(resp.text, "html5lib")
    data = {"url": ep_url}
    h1 = soup.select_one("h1")
    data["title"] = h1.text.strip() if h1 else ""
    data["overviews"] = {}
    data["directors"] = []
    data["writers"] = []
    data["imdb_id"] = ""
    data["tmdb_id"] = ""

    for li in soup.select("li.list-group-item"):
        strong = li.find("strong")
        if not strong:
            continue
        label = strong.text.strip().rstrip(":")
        span = li.find("span")
        value = span.get_text(" ", strip=True) if span else ""
        if "Originally Aired" in label:
            data["aired"] = value
        elif "Runtime" in label:
            nums = re.findall(r"\d+", value)
            data["runtime"] = nums[0] if nums else ""
        elif "Network" in label:
            data["network"] = value

    for div in soup.select(".change_translation_text"):
        lang = div.get("data-language", "")
        p = div.find("p")
        if p and p.text.strip():
            data["overviews"][lang] = p.text.strip()

    # Directors / Writers from castcrew table
    cast_tab = soup.find(id="castcrew")
    if cast_tab:
        for row in cast_tab.select("tbody tr"):
            cells = row.select("td")
            if len(cells) < 2:
                continue
            name_link = cells[0].find("a")
            if not name_link:
                continue
            name = name_link.text.strip()
            if not name or name in ("Add Person", "Add Character"):
                continue
            person_type = cells[1].text.strip().lower()
            if "director" in person_type:
                data["directors"].append(name)
            elif "writer" in person_type or "screenplay" in person_type:
                data["writers"].append(name)

    # External IDs
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if "imdb.com/title/" in href and not data["imdb_id"]:
            m = re.search(r"(tt\d+)", href)
            if m:
                data["imdb_id"] = m.group(1)
        if "themoviedb.org" in href and not data["tmdb_id"]:
            m = re.search(r"/(?:tv|movie)/(\d+)", href)
            if m:
                data["tmdb_id"] = m.group(1)

    return data


def pick_translation(mapping, fallback="", priority=None):
    if priority is None:
        priority = DEFAULT_PRIORITY
    for lang_key in priority:
        for k in LANG_GROUPS.get(lang_key, [lang_key]):
            if mapping.get(k):
                return mapping[k]
    return fallback


def fmt_date(text):
    if not text:
        return ""
    text = text.strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        return m.group(1)
    # Extract date-like portion: "December 21, 2014AT-X" -> "December 21, 2014"
    m2 = re.match(r"([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if m2:
        text = m2.group(1)
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return text


def fmt_year(text):
    m = re.search(r"(\d{4})", str(text or ""))
    return m.group(1) if m else ""


def safe_str(v):
    return str(v) if v else ""


def sub_el(parent, tag, text=None, attrib=None, cdata=False):
    el = etree.SubElement(parent, tag, attrib or {})
    if cdata and text:
        el.text = etree.CDATA(text)
    elif text is not None:
        el.text = str(text)
    return el


def make_xml_declaration(root):
    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True,
                               pretty_print=True, standalone=True)
    return xml_bytes.decode("utf-8")


def generate_tvshow_nfo(series_data, seasons, episodes_by_season, actors, lang, lang_priority=None):
    root = etree.Element("tvshow")

    ov = series_data.get("overviews", {})
    overview = pick_translation(ov, priority=lang_priority)
    sub_el(root, "plot", overview, cdata=True)
    sub_el(root, "outline", overview, cdata=True)
    sub_el(root, "lockdata", "false")
    sub_el(root, "dateadded", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    base_title = series_data.get("title", "")
    tr = series_data.get("title_translations", {})
    title = pick_translation(tr, base_title, priority=lang_priority)
    orig_title = tr.get("jpn") or base_title
    sub_el(root, "title", title)
    sub_el(root, "originaltitle", orig_title)

    for actor in actors:
        ael = etree.SubElement(root, "actor")
        sub_el(ael, "name", actor.get("name", ""))
        sub_el(ael, "role", actor.get("role", ""))
        sub_el(ael, "type", "Actor")

    sub_el(root, "rating", "0")
    yr = fmt_year(series_data.get("first_aired", ""))
    sub_el(root, "year", yr)
    sub_el(root, "sorttitle", title)

    cr = series_data.get("content_ratings", [])
    if cr:
        sub_el(root, "mpaa", cr[0])

    sid = series_data.get("series_id", "")
    imdb = series_data.get("imdb_id", "")
    tmdb = series_data.get("tmdb_id", "")

    sub_el(root, "imdb_id", imdb)
    sub_el(root, "tmdbid", tmdb)
    sub_el(root, "tvdbid", sid)

    premiered = fmt_date(series_data.get("first_aired", ""))
    if premiered:
        sub_el(root, "premiered", premiered)
        sub_el(root, "releasedate", premiered)

    all_eps = []
    for eps in episodes_by_season.values():
        all_eps.extend(eps)
    aired_dates = sorted([e.get("aired", "") for e in all_eps if e.get("aired")])
    if aired_dates:
        end_d = fmt_date(aired_dates[-1])
        if end_d:
            sub_el(root, "enddate", end_d)

    runtime = series_data.get("runtime", "")
    if runtime:
        sub_el(root, "runtime", runtime)

    for g in series_data.get("genres", []):
        sub_el(root, "genre", g)

    network = series_data.get("network", "")
    if network:
        sub_el(root, "studio", network)

    for t in series_data.get("tags", []):
        if t:
            sub_el(root, "tag", t)

    sub_el(root, "uniqueid", sid, {"type": "tvdb", "default": "true"})
    if imdb:
        sub_el(root, "uniqueid", imdb, {"type": "imdb"})
    if tmdb:
        sub_el(root, "uniqueid", tmdb, {"type": "tmdb"})

    ep_guide = {"tvdb": sid}
    if imdb:
        ep_guide["imdb"] = imdb
    if tmdb:
        ep_guide["tmdb"] = tmdb
    sub_el(root, "episodeguide", json.dumps(ep_guide, ensure_ascii=False))

    sub_el(root, "id", sid)
    sub_el(root, "season", "-1")
    sub_el(root, "episode", "-1")
    sub_el(root, "displayorder", "aired")
    sub_el(root, "status", series_data.get("status", ""))

    for tr_url in series_data.get("trailers", []):
        if tr_url:
            sub_el(root, "trailer", tr_url)

    # Artwork paths (relative)
    art_el = etree.SubElement(root, "art")
    if series_data.get("poster_path"):
        sub_el(art_el, "poster", series_data["poster_path"])
    if series_data.get("fanart_path"):
        sub_el(art_el, "fanart", series_data["fanart_path"])
    if series_data.get("clearlogo_path"):
        sub_el(art_el, "clearlogo", series_data["clearlogo_path"])
    if series_data.get("banner_path"):
        sub_el(art_el, "banner", series_data["banner_path"])

    return root


def generate_season_nfo(season_info, season_episodes):
    root = etree.Element("season")
    sn = season_info.get("number", 0)
    name = season_info.get("name", "Specials" if sn == 0 else f"Season {sn}")
    overview = ""
    sub_el(root, "plot", overview, cdata=True)
    sub_el(root, "outline", overview, cdata=True)
    sub_el(root, "lockdata", "false")
    sub_el(root, "dateadded", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sub_el(root, "title", name)
    aired_dates = [e.get("aired", "") for e in season_episodes if e.get("aired")]
    if aired_dates:
        sub_el(root, "year", fmt_year(sorted(aired_dates)[0]))
    elif season_info.get("from"):
        sub_el(root, "year", fmt_year(season_info["from"]))
    sub_el(root, "sorttitle", name)
    first_aired = season_info.get("from") or (sorted(aired_dates)[0] if aired_dates else "")
    premiered = fmt_date(first_aired)
    if premiered:
        sub_el(root, "premiered", premiered)
        sub_el(root, "releasedate", premiered)
    sub_el(root, "seasonnumber", str(sn))
    return root


def generate_episode_nfo(ep, series_data):
    root = etree.Element("episodedetails")
    overview = ep.get("overview") or ""
    if not overview:
        ov = ep.get("overviews", {})
        overview = ov.get("zho") or ov.get("jpn") or ov.get("eng") or ""
    sub_el(root, "plot", overview, cdata=True)
    sub_el(root, "outline", "")
    sub_el(root, "lockdata", "false")
    sub_el(root, "dateadded", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    sub_el(root, "title", ep.get("name", "") or ep.get("title", ""))
    for d in ep.get("directors", []):
        sub_el(root, "director", d)
    for w in ep.get("writers", []):
        sub_el(root, "writer", w)
    sub_el(root, "rating", "0")
    aired = ep.get("aired", "")
    if aired:
        sub_el(root, "year", fmt_year(aired))
        sub_el(root, "aired", fmt_date(aired))
    sub_el(root, "sorttitle", ep.get("name", ""))
    ep_runtime = ep.get("runtime", "")
    if ep_runtime:
        sub_el(root, "runtime", ep_runtime)
    epid = ep.get("id", "")
    sub_el(root, "tvdbid", epid)
    sub_el(root, "uniqueid", epid, {"type": "tvdb"})
    ep_imdb = ep.get("imdb_id", "")
    ep_tmdb = ep.get("tmdb_id", "")
    if ep_imdb:
        sub_el(root, "imdbid", ep_imdb)
        sub_el(root, "uniqueid", ep_imdb, {"type": "imdb"})
    if ep_tmdb:
        sub_el(root, "tmdbid", ep_tmdb)
        sub_el(root, "uniqueid", ep_tmdb, {"type": "tmdb"})
    sub_el(root, "episode", str(ep.get("number", "")))
    sub_el(root, "season", str(ep.get("seasonNumber", "")))
    if ep.get("thumb_local"):
        art_el = etree.SubElement(root, "art")
        sub_el(art_el, "poster", ep["thumb_local"])
    return root


def run(args):
    series_id = args.id
    series_url = args.url
    series_name = args.name

    if not series_id and series_url:
        m = re.search(r"/series/([^/]+)", series_url)
        slug = m.group(1) if m else ""
        if slug.isdigit():
            series_id = slug
            slug = resolve_slug(series_id)
        else:
            # Get ID from the page
            try:
                sd = scrape_series_page(slug)
                series_id = sd.get("series_id", "")
            except Exception:
                pass

    if not series_id and series_name:
        print(f"搜尋「{series_name}」...")
        results = search_series(series_name, args.lang)
        if not results:
            results = search_series(series_name, "en")
        if not results:
            print("找不到任何結果。")
            return

        if len(results) == 1:
            r = results[0]
            series_id = r["id"]
            print(f"找到: {r['name']} (ID: {series_id})")
        else:
            print(f"\n找到 {len(results)} 個結果:")
            print("-" * 60)
            for i, r in enumerate(results):
                yr = r.get("firstAired", "")[:4]
                print(f"  [{i+1}] {r['name']} ({yr})  TVDB ID: {r['id']}")
                ov = r.get("overview", "")[:80]
                if ov:
                    print(f"      {ov}...")
            print("-" * 60)
            choice = input(f"請選擇 (1-{len(results)}, q=離開): ").strip()
            if choice.lower() == "q":
                return
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(results):
                    series_id = results[idx]["id"]
                else:
                    print("無效選擇。")
                    return
            except ValueError:
                print("無效選擇。")
                return

    if not series_id:
        print("無法確定 Series ID。")
        return

    slug = resolve_slug(series_id)
    if not slug:
        print(f"無法解析 Series ID {series_id} 的網址。")
        return

    print(f"TVDB 網址: {BASE_URL}/series/{slug}")

    print("爬取系列資訊 ...")
    series_data = scrape_series_page(slug)
    title = series_data.get("title", slug)
    print(f"  標題: {title}")
    actors = series_data.get("actors", [])
    print(f"  季數: {len(series_data.get('seasons', []))}")
    print(f"  演員: {len(actors)} 位")

    episodes_by_season = {}
    if not args.no_episodes:
        seasons = series_data.get("seasons", [])
        for s_info in seasons:
            sn = s_info["number"]
            s_url = s_info["url"]
            if not s_url:
                continue
            print(f"爬取 {s_info['name']} ({s_info['episode_count']} 集) ...")
            eps = scrape_season_page(s_url)
            episodes_by_season[sn] = eps
            for ep in eps:
                ep_url = ep.get("url", "")
                if not ep_url:
                    continue
                print(f"  取得 {ep.get('name', '?')} 的詳細資訊 ...")
                try:
                    ep_detail = scrape_episode_page(ep_url)
                    ep["overviews"] = ep_detail.get("overviews", {})
                    ovs = ep_detail.get("overviews", {})
                    ep["overview"] = pick_translation(ovs, priority=DEFAULT_PRIORITY) or (list(ovs.values())[0] if ovs else "")
                    ep["directors"] = ep_detail.get("directors", [])
                    ep["writers"] = ep_detail.get("writers", [])
                    ep["imdb_id"] = ep_detail.get("imdb_id", "")
                    ep["tmdb_id"] = ep_detail.get("tmdb_id", "")
                    if ep_detail.get("aired"):
                        ep["aired"] = ep_detail["aired"]
                    if ep_detail.get("runtime"):
                        ep["runtime"] = ep_detail["runtime"]
                except Exception as e:
                    print(f"    警告: {e}")
                time.sleep(0.5)

    output_dir = Path(args.output)
    safe_title = "".join(c for c in title if c not in r'\/:*?"<>|')
    if not args.url:
        output_dir = output_dir / safe_title
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download series artwork
    images = series_data.get("images", {})
    sid_str = series_data.get("series_id", "")
    print("\n下載系列圖片 ...")
    if images.get("poster"):
        poster_path = output_dir / "poster.jpg"
        if download_image(images["poster"], poster_path):
            series_data["poster_path"] = str(poster_path.resolve())
            print(f"  poster.jpg")
    if images.get("fanart"):
        fanart_path = output_dir / "fanart.jpg"
        if download_image(images["fanart"], fanart_path):
            series_data["fanart_path"] = str(fanart_path.resolve())
            print(f"  fanart.jpg")
    if images.get("clearlogo"):
        ext = ".png" if images["clearlogo"].lower().endswith(".png") else ".jpg"
        clearlogo_path = output_dir / f"clearlogo{ext}"
        if download_image(images["clearlogo"], clearlogo_path):
            series_data["clearlogo_path"] = str(clearlogo_path.resolve())
            print(f"  clearlogo{ext}")
    if images.get("banner"):
        banner_path = output_dir / "banner.jpg"
        if download_image(images["banner"], banner_path):
            series_data["banner_path"] = str(banner_path.resolve())
            print(f"  banner.jpg")

    # Download season posters
    for s_info in series_data.get("seasons", []):
        sn = s_info["number"]
        season_dir_name = "Specials" if sn == 0 else f"Season {sn}"
        season_dir = output_dir / season_dir_name
        season_dir.mkdir(parents=True, exist_ok=True)
        simg = scrape_season_images(s_info.get("url", ""), sid_str, sn)
        poster_name = f"season{sn:02d}-poster.jpg" if sn > 0 else "season-specials-poster.jpg"
        if simg.get("poster"):
            download_image(simg["poster"], season_dir / poster_name)
            s_info["poster_local"] = poster_name
        time.sleep(0.3)

    # Download episode thumbnails
    for s_info in series_data.get("seasons", []):
        sn = s_info["number"]
        eps = episodes_by_season.get(sn, [])
        season_dir_name = "Specials" if sn == 0 else f"Season {sn}"
        season_dir = output_dir / season_dir_name
        season_dir.mkdir(parents=True, exist_ok=True)
        for ep in eps:
            ep_thumb = get_episode_image_url(sid_str, ep.get("id", ""))
            thumb_name = f"S{ep.get('seasonNumber', sn):02d}E{ep.get('number', 0):02d}-thumb.jpg"
            if download_image(ep_thumb, season_dir / thumb_name):
                ep["thumb_local"] = thumb_name
            time.sleep(0.2)

    print("\n產生 tvshow.nfo ...")
    tvshow_root = generate_tvshow_nfo(series_data, series_data.get("seasons", []),
                                       episodes_by_season, actors, args.lang, DEFAULT_PRIORITY)
    tvshow_xml = make_xml_declaration(tvshow_root)
    tvshow_path = output_dir / "tvshow.nfo"
    tvshow_path.write_text(tvshow_xml, encoding="utf-8")
    print(f"  -> {tvshow_path}")

    if args.no_episodes:
        print("完成！")
        return

    for s_info in series_data.get("seasons", []):
        sn = s_info["number"]
        eps = episodes_by_season.get(sn, [])
        if not eps:
            continue
        season_dir_name = "Specials" if sn == 0 else f"Season {sn}"
        season_dir = output_dir / season_dir_name
        season_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{season_dir_name} ({len(eps)} 集)")

        season_root = generate_season_nfo(s_info, eps)
        season_xml = make_xml_declaration(season_root)
        nfo_path = season_dir / "season.nfo"
        nfo_path.write_text(season_xml, encoding="utf-8")
        print(f"  產生 season.nfo")

        for ep in sorted(eps, key=lambda e: int(e.get("number", 0))):
            ep_num = ep.get("number", 0)
            ep_season = ep.get("seasonNumber", sn)
            ep_filename = f"S{ep_season:02d}E{ep_num:02d}.nfo"
            ep_root = generate_episode_nfo(ep, series_data)
            ep_xml = make_xml_declaration(ep_root)
            ep_path = season_dir / ep_filename
            ep_path.write_text(ep_xml, encoding="utf-8")
            print(f"    {ep_filename}")

    print(f"\n{'=' * 55}")
    print(f"  完成！NFO 輸出到: {output_dir.resolve()}")
    print(f"{'=' * 55}")


def main():
    parser = argparse.ArgumentParser(description="TheTVDB NFO Crawler (純爬蟲，不需 API Key)")
    parser.add_argument("name", nargs="?", help="動漫名稱")
    parser.add_argument("-u", "--url", help="TheTVDB 系列網址")
    parser.add_argument("-i", "--id", help="TheTVDB 系列 ID")
    parser.add_argument("-o", "--output", default=".", help="輸出目錄")
    parser.add_argument("-l", "--lang", default="zho", help="語言代碼 (zho/jpn/eng)")
    parser.add_argument("--no-episodes", action="store_true", help="只產生 tvshow.nfo")
    args = parser.parse_args()

    if not args.name and not args.url and not args.id:
        print("TheTVDB NFO Crawler (純爬蟲版)")
        print("=" * 55)
        while True:
            q = input("\n請輸入動漫名稱 / TVDB網址 / TVDB ID (q 離開): ").strip()
            if q.lower() == "q":
                break
            if not q:
                continue
            if q.startswith("http"):
                args.url = q
            elif q.isdigit():
                args.id = q
            else:
                args.name = q
            run(args)
            break
        return

    run(args)


if __name__ == "__main__":
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        except Exception:
            pass
    main()
