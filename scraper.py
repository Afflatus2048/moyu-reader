"""Scraper: fetch, parse and cache novel content - supports multiple sites"""

import json, time, re, os, hashlib
from datetime import datetime
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from config import CACHE_DIR, REQUEST_DELAY, REQUEST_TIMEOUT

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_last_req = 0.0

def _throttle():
    global _last_req
    elapsed = time.time() - _last_req
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_req = time.time()

def fetch_page(url):
    _throttle()
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
        # Auto-detect encoding: try utf-8 first, then gb18030
        r.encoding = r.apparent_encoding or 'utf-8'
        text = r.text
        # Validate: if text has mostly replacement chars, try other encodings
        if '�' in text[:500]:
            for enc in ['gb18030', 'gbk', 'big5']:
                try:
                    text = r.content.decode(enc)
                    if '�' not in text[:500]:
                        break
                except: continue
        return text
    except Exception:
        return None

def extract_book_id(url):
    """Generate a stable book ID from URL."""
    # Try to extract from URL patterns
    m = re.search(r"/book/(\d+)", url)
    if m: return m.group(1)
    m = re.search(r"/n/([\w-]+)/", url)
    if m: return m.group(1)
    # Fallback: hash the URL
    return hashlib.md5(url.encode()).hexdigest()[:12]

# ── Parse catalog (generic) ──

def parse_toc(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    # Book title: try multiple sources
    title = ""
    og = soup.find("meta", property="og:novel:book_name")
    if og: title = og.get("content", "")
    if not title:
        for sel in ["h1", "h2", ".book-title", ".novel-title"]:
            el = soup.select_one(sel)
            if el:
                title = el.text.strip()
                break
    if not title:
        title = "Unknown Novel"

    chapters = []
    # Strategy 1: find links that look like chapter pages under the same book path
    base_path = ""
    m = re.search(r"/(n/[\w-]+|book/\d+)", base_url)
    if m: base_path = m.group(1)

    seen = set()
    for a in soup.select("a"):
        href = a.get("href", "")
        name = a.text.strip()
        if not name or not href: continue
        if len(name) > 50: continue  # skip long non-chapter links

        # Must be under the same book path
        if base_path and base_path not in href:
            # Also accept relative URLs like "2.html"
            if not href.startswith("/") and not href.startswith("http"):
                href = urljoin(base_url, href)
                if base_path not in href: continue
            else: continue

        # Generate chapter ID
        # Pattern: /n/name/2.html -> "2", /book/22249/1075080.html -> "1075080"
        ch_id = None
        m2 = re.search(r"/(\d+)\.html", href)
        if m2: ch_id = m2.group(1)
        if not ch_id:
            m2 = re.search(r"/(\d+)", href)
            if m2: ch_id = m2.group(1)
        if not ch_id: continue

        # Skip duplicates and non-chapter entries
        if ch_id in seen: continue
        seen.add(ch_id)

        # Build full URL
        full_url = urljoin(base_url, href)

        chapters.append({"id": ch_id, "name": name, "url": full_url})

    # Sort by chapter ID numerically if all are numbers
    if all(c["id"].isdigit() for c in chapters):
        chapters.sort(key=lambda c: int(c["id"]))

    return {"book_id": extract_book_id(base_url), "title": title, "chapters": chapters}

# ── Parse chapter content (generic) ──

def parse_chapter(html):
    soup = BeautifulSoup(html, "html.parser")

    # Title: try h1, h2, h3
    title = ""
    for sel in ["h1", "h2", "h3", ".chapter-title", ".nr_title"]:
        el = soup.select_one(sel)
        if el:
            title = el.text.strip()
            break

    # Content: try multiple selectors
    content_div = None
    for sel in ["#content", ".chapter_content", "#BookText", "#booktxt",
                ".content", ".nr1", ".read-content", ".chapter-content"]:
        content_div = soup.select_one(sel)
        if content_div: break

    paragraphs = []
    if content_div:
        text = content_div.get_text(separator="\n")
        for line in text.split("\n"):
            line = line.strip().replace("\xa0", "")
            if not line: continue
            # Skip ad lines
            ad_keywords = ["jiugangbi", "旧钢笔", "dingdian", "顶点", "提供", "免费阅读",
                           "本章未完", "点击下一页", "手机阅读", "推荐阅读"]
            if any(kw in line for kw in ad_keywords): continue
            paragraphs.append(line)

    # Detect next page
    next_page_url = None
    for a in soup.select("a"):
        href = a.get("href", "")
        text_a = a.text.strip()
        if "_2" in href or "_3" in href or "下一页" in text_a:
            next_page_url = href
            break

    return {"title": title, "paragraphs": paragraphs, "next_page_url": next_page_url}

# ── Multi-page merge ──

def fetch_chapter_full(url):
    """Fetch a chapter, merging all pages."""
    all_paragraphs = []
    title = ""
    current_url = url
    page = 1

    while current_url and page <= 20:
        html = fetch_page(current_url)
        if not html: break
        parsed = parse_chapter(html)
        if page == 1: title = parsed["title"]
        all_paragraphs.extend(parsed["paragraphs"])

        np = parsed["next_page_url"]
        if np:
            if not np.startswith("http"):
                np = urljoin(current_url, np)
            current_url = np
            page += 1
        else:
            # Try predicting _2.html
            if page == 1:
                predict = url.replace(".html", "_2.html")
                test_html = fetch_page(predict)
                if test_html:
                    test_parsed = parse_chapter(test_html)
                    if test_parsed["paragraphs"]:
                        all_paragraphs.extend(test_parsed["paragraphs"])
                        # Try _3.html
                        predict3 = url.replace(".html", "_3.html")
                        test3 = fetch_page(predict3)
                        if test3:
                            p3 = parse_chapter(test3)
                            if p3["paragraphs"]:
                                all_paragraphs.extend(p3["paragraphs"])
            break

    return {"title": title, "paragraphs": all_paragraphs}

# ── Cache ──

def _book_dir(book_id):
    d = os.path.join(CACHE_DIR, book_id)
    os.makedirs(d, exist_ok=True)
    return d

def load_toc_cache(book_id):
    path = os.path.join(_book_dir(book_id), "toc.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_toc_cache(book_id, toc):
    path = os.path.join(_book_dir(book_id), "toc.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(toc, f, ensure_ascii=False)

def load_chapter_cache(book_id, chapter_id):
    path = os.path.join(_book_dir(book_id), f"{chapter_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_chapter_cache(book_id, chapter_id, data):
    path = os.path.join(_book_dir(book_id), f"{chapter_id}.json")
    data["cached_at"] = datetime.now().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def get_or_fetch_chapter(book_id, chapter_id, url):
    cached = load_chapter_cache(book_id, chapter_id)
    if cached: return cached
    result = fetch_chapter_full(url)
    save_chapter_cache(book_id, chapter_id, result)
    return result