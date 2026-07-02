"""MoYu Reader - Flask application"""

import os, threading
from flask import Flask, render_template, request, jsonify
from scraper import (fetch_page, parse_toc, extract_book_id,
                     load_toc_cache, save_toc_cache,
                     get_or_fetch_chapter)
from disguise import disguise_chapter, disguise_text_replace
from config import HOST, PORT

app = Flask(__name__, static_folder='static', template_folder='templates')

def _filter_chapters(toc):
    return [c for c in toc["chapters"] if not _skip(c["name"])]

def _skip(name):
    import re
    return bool(re.match(r"^\d+-\d+$", name.strip()))

def _prefetch_book(book_id, chapters, count=5):
    """Background prefetch: fetch first N chapters."""
    for ch in chapters[:count]:
        try:
            get_or_fetch_chapter(book_id, ch["id"], ch["url"])
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
        "chapters": [{"id": c["id"], "name": c["name"], "index": i} for i, c in enumerate(chapters)],
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
    mode = request.args.get("mode", "code")
    if mode == "replace":
        lines, lang = disguise_text_replace(data["title"], data["paragraphs"])
    else:
        lines, lang = disguise_chapter(data["title"], data["paragraphs"])

    prev_id = chapters[idx - 1]["id"] if idx > 0 else None
    next_id = chapters[idx + 1]["id"] if idx < len(chapters) - 1 else None

    # Prefetch next chapter in background
    if next_id:
        next_ch = chapters[idx + 1]
        threading.Thread(target=get_or_fetch_chapter, args=(book_id, next_ch["id"], next_ch["url"]), daemon=True).start()

    return jsonify({
        "success": True,
        "chapter_id": chapter_id,
        "title": data["title"],
        "index": idx,
        "total": len(chapters),
        "prev_id": prev_id,
        "next_id": next_id,
        "lines": lines,
        "lang": lang,
    })

if __name__ == "__main__":
    import webbrowser
    url = f"http://{HOST}:{PORT}"
    print(f"MoYu Reader running at {url}")
    webbrowser.open(url)
    app.run(host=HOST, port=PORT, debug=False)