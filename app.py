"""MoYu Reader - Flask application"""

import os, threading
from flask import Flask, render_template, request, jsonify
from scraper import (fetch_page, parse_toc, extract_book_id,
                     load_toc_cache, save_toc_cache,
                     get_or_fetch_chapter, save_chapter_cache)
from disguise import disguise_chapter, disguise_text_replace
from config import HOST, PORT, CACHE_DIR

app = Flask(__name__, static_folder='static', template_folder='templates')

def _filter_chapters(toc):
    return [c for c in toc["chapters"] if not _skip(c["name"])]

def _skip(name):
    import re
    return bool(re.match(r"^\d+-\d+$", name.strip()))

def _extract_chapter_num(name):
    """Extract chapter number from name like '第105章' → 105, 'Chapter 42' → 42."""
    import re
    # Chinese pattern: 第N章
    m = re.search(r'第\s*(\d+)\s*章', name)
    if m: return int(m.group(1))
    # English pattern: Chapter N
    m = re.search(r'[Cc]hapter\s+(\d+)', name)
    if m: return int(m.group(1))
    return None

def _prefetch_book(book_id, chapters, count=5):
    """Background prefetch: fetch first N chapters."""
    for ch in chapters[:count]:
        try:
            get_or_fetch_chapter(book_id, ch["id"], ch["url"])
        except Exception:
            pass

def _sliding_cache(book_id, chapters, current_idx, mode='replace', window=2):
    """Sliding window cache around current reading position.

    - Raw-cache chapters in [current - window, current + window]
    - Pre-DISGUISE the immediate next chapter (most likely navigation target)
    - Delete chapters outside [current - window - 1, current + window]
      (keep 1 extra behind for back-navigation)
    """
    start = max(0, current_idx - window)
    end = min(len(chapters), current_idx + window + 1)

    # 1. Raw-cache all chapters in window
    for ch in chapters[start:end]:
        try:
            get_or_fetch_chapter(book_id, ch["id"], ch["url"])
        except Exception:
            pass

    # 2. Pre-disguise the NEXT chapter so "next" nav is instant
    next_idx = current_idx + 1
    if next_idx < len(chapters):
        ch = chapters[next_idx]
        try:
            data = get_or_fetch_chapter(book_id, ch["id"], ch["url"])
            cache_key = f"disguised_{mode}"
            if data and (cache_key not in data or not data[cache_key].get("lines")):
                if mode == "replace":
                    lines, lang = disguise_chapter(data["title"], data["paragraphs"], replace_words=True)
                else:
                    lines, lang = disguise_chapter(data["title"], data["paragraphs"])
                data[cache_key] = {"lines": lines, "lang": lang}
                save_chapter_cache(book_id, ch["id"], data)
        except Exception:
            pass

    # 3. Delete chapters outside sliding window
    delete_before = max(0, current_idx - window - 1)  # keep 1 extra behind
    delete_after = min(len(chapters), current_idx + window + 1)

    for i, ch in enumerate(chapters):
        if i < delete_before or i >= delete_after:
            try:
                path = os.path.join(CACHE_DIR, book_id, f"{ch['id']}.json")
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/book/load", methods=["POST"])
def load_book():
    url = request.json.get("url", "").strip()
    if not url: return jsonify({"success": False, "error": "URL required"})

    book_id = extract_book_id(url)
    if not book_id: return jsonify({"success": False, "error": "Cannot extract book ID from URL"})

    toc = load_toc_cache(book_id)
    if not toc:
        html = fetch_page(url)
        if not html: return jsonify({"success": False, "error": "Failed to fetch page"})
        toc = parse_toc(html, url)
        if not toc["chapters"]: return jsonify({"success": False, "error": "No chapters found"})
        save_toc_cache(book_id, toc)

    chapters = _filter_chapters(toc)

    # Background prefetch first 5 chapters
    threading.Thread(target=_prefetch_book, args=(book_id, chapters, 5), daemon=True).start()

    return jsonify({
        "success": True,
        "book_id": toc["book_id"],
        "title": toc["title"],
        "chapters": [{"id": c["id"], "name": c["name"], "index": i,
                      "num": _extract_chapter_num(c["name"])}
                     for i, c in enumerate(chapters)],
    })

@app.route("/api/chapter/<book_id>/<chapter_id>")
def get_chapter(book_id, chapter_id):
    toc = load_toc_cache(book_id)
    if not toc:
        return jsonify({"success": False, "error": "Book not loaded"})

    chapters = _filter_chapters(toc)
    idx = None
    for i, c in enumerate(chapters):
        if c["id"] == chapter_id:
            idx = i
            break

    if idx is None:
        return jsonify({"success": False, "error": "Chapter not found"})

    chapter = chapters[idx]

    # Get chapter content (cached or fetch)
    data = get_or_fetch_chapter(book_id, chapter_id, chapter["url"])
    if not data or not data["paragraphs"]:
        return jsonify({"success": False, "error": "Failed to fetch chapter content"})

    # Disguise - support "code" (default) and "replace" modes
    # Check if disguised output is already cached (major speedup on revisit)
    mode = request.args.get("mode", "replace")
    cache_key = f"disguised_{mode}"

    if cache_key in data and data[cache_key].get("lines"):
        lines = data[cache_key]["lines"]
        lang = data[cache_key]["lang"]
    else:
        if mode == "replace":
            lines, lang = disguise_chapter(data["title"], data["paragraphs"], replace_words=True)
        else:
            lines, lang = disguise_chapter(data["title"], data["paragraphs"])
        # Cache the disguised output so next visit is instant (sync to avoid races)
        data[cache_key] = {"lines": lines, "lang": lang}
        save_chapter_cache(book_id, chapter_id, data)

    prev_id = chapters[idx - 1]["id"] if idx > 0 else None
    next_id = chapters[idx + 1]["id"] if idx < len(chapters) - 1 else None

    # Sliding window cache: raw-cache ±2, pre-disguise next chapter, delete out-of-window
    threading.Thread(target=_sliding_cache, args=(book_id, chapters, idx, mode), daemon=True).start()

    # Extract chapter number from the fetched content title
    chapter_num = _extract_chapter_num(data.get("title", ""))
    # Fall back to TOC chapter name extraction
    if chapter_num is None:
        chapter_num = _extract_chapter_num(chapter["name"])

    return jsonify({
        "success": True,
        "chapter_id": chapter_id,
        "title": data["title"],
        "index": idx,
        "total": len(chapters),
        "prev_id": prev_id,
        "next_id": next_id,
        "chapter_num": chapter_num,
        "lines": lines,
        "lang": lang,
    })

if __name__ == "__main__":
    import webbrowser
    url = f"http://{HOST}:{PORT}"
    print(f"MoYu Reader running at {url}")
    webbrowser.open(url)
    app.run(host=HOST, port=PORT, debug=False)