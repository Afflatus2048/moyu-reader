"""Disguise engine: convert novel text to comment-embedded code"""

import unicodedata, random, re

MAX_LINE_COLS = 76

# Pre-load jieba to avoid per-request dictionary loading lag
_jieba_loaded = False

def _ensure_jieba():
    global _jieba_loaded
    if not _jieba_loaded:
        import jieba
        jieba.cut("初始化")
        _jieba_loaded = True

# ── Character width ──

def char_width(c):
    eaw = unicodedata.east_asian_width(c)
    if eaw in ('W', 'F'): return 2
    if eaw == 'A': return 2
    return 1

def display_width(s):
    return sum(char_width(c) for c in s)

# ── Split paragraph into lines ──

BREAK_AFTER = set('，。！？；：、…—""''）】》')

def split_to_lines(text, max_cols=MAX_LINE_COLS, indent=4):
    usable = max_cols - indent
    lines = []
    current = ""
    width = 0
    for c in text:
        cw = char_width(c)
        if width + cw > usable:
            best_break = -1
            for i, ch in enumerate(current):
                if ch in BREAK_AFTER and display_width(current[:i+1]) >= usable * 0.6:
                    best_break = i
            if best_break >= 0:
                lines.append(current[:best_break+1])
                current = current[best_break+1:] + c
                width = display_width(current)
            else:
                lines.append(current)
                current = c
                width = cw
        else:
            current += c
            width += cw
    if current:
        lines.append(current)
    return lines

# ── Realistic Python code generator ──
# Generates code line-by-line, inserting novel content as # comments
# at natural positions, with indentation matching the surrounding code.

# A "code state" tracks current indent level, class/method context, etc.
# This ensures comments align with surrounding code naturally.

class CodeGen:
    """Generate realistic Python code with novel content as comments."""

    # Comment density: about 1 comment every 7-9 code lines (10-14%)
    COMMENT_INTERVAL = 8  # average lines between comments

    # Comment lengths: 1-3 consecutive comment lines
    COMMENT_LENGTHS = [1, 1, 2, 2, 2, 3]  # weighted: mostly 1-2 lines

    # Method names pool
    METHOD_NAMES = [
        "process_data", "validate_input", "transform_content",
        "parse_response", "handle_request", "calculate_metrics",
        "format_output", "check_status", "merge_records",
        "update_cache", "build_index", "resolve_target",
        "extract_fields", "sort_entries", "filter_results",
        "compute_hash", "load_config", "save_state",
        "initialize_pool", "register_hook", "dispatch_event",
    ]

    CLASS_NAMES = [
        "DataProcessor", "ConfigManager", "RequestHandler",
        "CacheService", "TaskScheduler", "PipelineRunner",
        "AuthProvider", "MetricsCollector", "EventDispatcher",
        "ResponseBuilder", "StateManager", "IndexManager",
    ]

    VAR_NAMES = [
        "result", "data", "config", "payload", "response",
        "output", "status", "records", "entries", "items",
        "values", "keys", "fields", "params", "options",
        "content", "buffer", "cache", "index", "queue",
    ]

    def __init__(self):
        self.indent = 0  # current indent level (0=top, 1=class, 2=method, 3=inside method)
        self.lines = []
        self._line_counter = 0  # lines since last comment
        self._next_comment_at = random.randint(6, 10)
        self._used_methods = set()
        self._used_classes = set()

    def _pick(self, pool, used):
        avail = [n for n in pool if n not in used]
        if not avail: avail = pool
        name = random.choice(avail)
        used.add(name)
        return name

    def _ind(self):
        """Return indent string for current level."""
        return "    " * self.indent

    def _emit(self, line):
        """Add a code line."""
        self.lines.append(self._ind() + line)
        self._line_counter += 1

    def _emit_raw(self, line):
        """Add a line with no indent adjustment (already formatted)."""
        self.lines.append(line)
        self._line_counter += 1

    def _emit_comment(self, novel_text):
        """Add a comment line with current indent."""
        self.lines.append(self._ind() + "# " + novel_text)

    def _maybe_insert_comments(self, novel_lines, novel_idx):
        """Check if it's time to insert novel comment lines."""
        if self._line_counter >= self._next_comment_at and novel_idx < len(novel_lines):
            count = random.choice(self.COMMENT_LENGTHS)
            inserted = 0
            for _ in range(count):
                if novel_idx + inserted < len(novel_lines):
                    self._emit_comment(novel_lines[novel_idx + inserted])
                    inserted += 1
            self._line_counter = 0
            self._next_comment_at = random.randint(6, 10)
            return inserted
        return 0

    # ── Code generation methods ──

    def gen_file_header(self, title):
        self._emit_raw('"""')
        self._emit_raw(f'Module: {title}')
        self._emit_raw('Data processing and analysis pipeline.')
        self._emit_raw('"""')
        self._emit_raw('')
        for imp in [
            'import os, sys, json, logging, time, hashlib',
            'from typing import Dict, List, Optional, Any, Tuple, Callable',
            'from datetime import datetime, timedelta',
            'from collections import defaultdict, OrderedDict',
            'from functools import wraps, lru_cache',
        ]:
            self._emit_raw(imp)
        self._emit_raw('')
        self._emit_raw('logger = logging.getLogger(__name__)')
        self._emit_raw('')
        self.indent = 0

    def gen_class(self):
        name = self._pick(self.CLASS_NAMES, self._used_classes)
        self._emit(f"class {name}:")
        desc = random.choice([
            f"Handle {name.lower().replace('handler','').replace('processor','data').replace('manager','config').strip()} operations.",
            f"Core {name.lower().split('handler')[0].split('processor')[0].split('manager')[0].strip() or 'service'} implementation.",
            f"Manage {name.lower().replace('manager','').replace('service','').strip() or 'internal'} state and processing.",
        ])
        self.indent += 1
        self._emit(f'"""{desc}"""')
        self._emit('')
        return name

    def gen_init(self, class_name):
        self._emit("def __init__(self, config: Dict[str, Any]):")
        self.indent += 1
        self._emit("self._config = config")
        self._emit("self._initialized = False")
        for var, val in random.sample([
            ("timeout", "config.get('timeout', 30)"),
            ("max_retries", "config.get('max_retries', 3)"),
            ("cache_enabled", "config.get('cache_enabled', True)"),
            ("batch_size", "config.get('batch_size', 100)"),
            ("verbose", "config.get('verbose', False)"),
            ("debug", "config.get('debug', False)"),
            ("pool_size", "config.get('pool_size', 10)"),
        ], k=min(4, 7)):
            self._emit(f"self.{var} = {val}")
        self._emit("self._results: Dict[str, Any] = {}")
        self._emit("self._errors: List[str] = []")
        self._emit("self._state = 'initialized'")
        self._emit("logger.info(f'{class_name} initialized with config')")
        self.indent -= 1
        self._emit('')
        return class_name

    def gen_method(self):
        name = self._pick(self.METHOD_NAMES, self._used_methods)
        params = random.choice([
            "self, data: Dict[str, Any]",
            "self, input: str",
            "self, payload: Optional[Dict] = None",
            "self, records: List[Any]",
            "self, key: str, value: Any",
        ])
        self._emit(f"def {name}({params}):")
        self.indent += 1
        return name

    def gen_method_body(self, method_name, novel_lines, novel_idx):
        """Generate method body with occasional novel comments."""
        bodies = {
            "process_data": [
                "if not data:",
                "    logger.warning('Empty data received')",
                "    return {}",
                "result = self._transform(data)",
                "if self.cache_enabled:",
                "    self._cache_result(result)",
                "self._results[method_name] = result",
                "return result",
            ],
            "validate_input": [
                "required = self._config.get('required_fields', [])",
                "for field in required:",
                "    if field not in data:",
                "        self._errors.append(f'Missing: {field}')",
                "        return False",
                "return len(self._errors) == 0",
            ],
            "transform_content": [
                "output = {}",
                "for key, value in data.items():",
                "    if isinstance(value, str):",
                "        output[key] = value.strip().lower()",
                "    else:",
                "        output[key] = value",
                "return output",
            ],
            "parse_response": [
                "try:",
                "    parsed = json.loads(input)",
                "    if 'error' in parsed:",
                "        logger.error(f'API error: {parsed[\"error\"]}')",
                "        return None",
                "    return parsed",
                "except json.JSONDecodeError as e:",
                "    logger.warning(f'Parse failed: {e}')",
                "    return None",
            ],
            "handle_request": [
                "self._state = 'processing'",
                "for attempt in range(self.max_retries):",
                "    try:",
                "        result = self._execute(payload)",
                "        self._state = 'completed'",
                "        return result",
                "    except Exception as e:",
                "        logger.error(f'Attempt {attempt+1} failed: {e}')",
                "self._state = 'failed'",
                "raise RuntimeError(f'Failed after {self.max_retries} attempts')",
            ],
            "calculate_metrics": [
                "metrics = {}",
                "metrics['total'] = len(records)",
                "metrics['valid'] = sum(1 for r in records if self._is_valid(r))",
                "metrics['invalid'] = metrics['total'] - metrics['valid']",
                "metrics['rate'] = metrics['valid'] / metrics['total'] if metrics['total'] > 0 else 0",
                "logger.info(f'Calculated metrics: {metrics}')",
                "return metrics",
            ],
            "format_output": [
                "if not data:",
                "    return ''",
                "lines = []",
                "for key, value in sorted(data.items()):",
                "    lines.append(f'{key}: {value}')",
                "return '\\n'.join(lines)",
            ],
            "check_status": [
                "status = {",
                "    'state': self._state,",
                "    'results': len(self._results),",
                "    'errors': len(self._errors),",
                "    'initialized': self._initialized,",
                "}",
                "return status",
            ],
            "merge_records": [
                "merged = []",
                "seen = set()",
                "for record in records:",
                "    key = self._compute_key(record)",
                "    if key not in seen:",
                "        merged.append(record)",
                "        seen.add(key)",
                "return merged",
            ],
            "compute_hash": [
                "raw = json.dumps(data, sort_keys=True)",
                "return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]",
            ],
            "load_config": [
                "path = Path(self._config.get('config_path', 'config.json'))",
                "if not path.exists():",
                "    logger.warning(f'Config not found: {path}')",
                "    return self._config",
                "with open(path) as f:",
                "    loaded = json.load(f)",
                "return {**self._config, **loaded}",
            ],
            "save_state": [
                "path = Path(self._config.get('state_path', 'state.json'))",
                "state = {",
                "    'results': self._results,",
                "    'errors': self._errors,",
                "    'state': self._state,",
                "    'timestamp': datetime.now().isoformat(),",
                "}",
                "with open(path, 'w') as f:",
                "    json.dump(state, f, indent=2)",
            ],
            "build_index": [
                "index = {}",
                "for item in data:",
                "    for key in self._extract_keys(item):",
                "        if key not in index:",
                "            index[key] = []",
                "        index[key].append(item)",
                "return index",
            ],
        }

        # Use predefined body if available, else generic
        body = bodies.get(method_name, [
            "if not data:",
            "    return None",
            "processed = self._apply_transform(data)",
            "self._results[method_name] = processed",
            "return processed",
        ])

        inserted = 0
        for i, line in enumerate(body):
            # Check indent of this line
            stripped = line.lstrip()
            spaces = len(line) - len(stripped)
            # Adjust indent: method body is at self.indent + spaces/4
            body_indent = self.indent + spaces // 4
            self.lines.append("    " * body_indent + stripped)
            self._line_counter += 1

            # Maybe insert comment after this line
            n = self._maybe_insert_comments(novel_lines, novel_idx + inserted)
            inserted += n

        self.indent -= 1
        self._emit('')
        return inserted

    def gen_method_close(self):
        self.indent -= 1
        self._emit('')

    def gen_footer(self):
        self._emit_raw('')
        self._emit_raw('if __name__ == "__main__":')
        self._emit_raw('    config = {"timeout": 30, "max_retries": 3, "cache_enabled": True}')
        cls = list(self._used_classes)[-1] if self._used_classes else "DataProcessor"
        self._emit_raw(f'    handler = {cls}(config)')
        self._emit_raw('    result = handler.process_data({"key": "value"})')
        self._emit_raw('    print(json.dumps(result, indent=2))')


# ── Context-aware word translation ──
# Two-pass approach:
# 1. Translate target word alone → en_word
# 2. Translate short context phrase (word + neighbors) → en_ctx
# 3. If en_word appears inside en_ctx → confirmed correct, use en_word
# 4. Otherwise, the word is ambiguous → extract short key word(s) from en_ctx
# Display format: English（中文词）— always 1-2 words of English

_translation_cache = {}
MAX_TRANSLATIONS_PER_CHAPTER = 25

# English function words to strip when extracting key content words
_FUNCTION_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from', 'into',
    'and', 'or', 'but', 'not', 'no', 'this', 'that', 'it', 'as', 'so',
    'will', 'would', 'could', 'should', 'may', 'might', 'can', 'shall',
    'has', 'have', 'had', 'do', 'does', 'did', 'very', 'just', 'also',
    'then', 'if', 'when', 'where', 'how', 'what', 'which', 'who', 'why',
    'some', 'any', 'all', 'both', 'each', 'every', 'few', 'more', 'most',
    'other', 'such', 'only', 'own', 'same', 'too', 'about', 'up', 'out',
    'he', 'she', 'they', 'them', 'their', 'his', 'her', 'its', 'our',
    'i', 'me', 'my', 'we', 'us', 'you', 'your', 'one', 'two', 'there',
}


def _translate_text(text):
    """Translate text via Google Translate, with in-memory caching."""
    if text in _translation_cache:
        return _translation_cache[text]
    try:
        from deep_translator import GoogleTranslator
        result = GoogleTranslator(source='zh-CN', target='en').translate(text)
        if result and result != text and len(result.strip()) > 0:
            _translation_cache[text] = result.strip()
            return _translation_cache[text]
    except Exception:
        pass
    _translation_cache[text] = text
    return text


def _extract_keyword(en_text):
    """Extract 1-2 key content words from an English phrase, stripping function words.
    Preserves meaningful pairs like 'used to', 'going to', etc."""
    raw_words = [w.strip('.,!?;:()[]"\'') for w in en_text.split()]
    content = []
    i = 0
    while i < len(raw_words):
        w = raw_words[i]
        if w.lower() in _FUNCTION_WORDS:
            # Check if this function word pairs with previous content word
            if content and w.lower() in ('to',) and i > 0:
                content[-1] = content[-1] + ' ' + w
            i += 1
            continue
        if len(w) > 1:
            content.append(w)
        i += 1
    if not content:
        return raw_words[0] if raw_words else en_text
    return ' '.join(content[:2])


def _translate_word_smart(word, context_words, word_idx):
    """Translate a Chinese word to English, using context to disambiguate.

    1. Translate the word alone
    2. Translate a short context phrase (word + 1 neighbor each side)
    3. If solo translation ≤ 2 words: trust it (Google's context rephrase, not wrong)
    4. If solo is longer AND disagrees with context: fall back to keyword extraction
    """
    en_solo = _translate_text(word)

    # Build minimal context phrase
    start = max(0, word_idx - 1)
    end = min(len(context_words), word_idx + 2)
    ctx_phrase = ''.join(context_words[start:end])

    if ctx_phrase == word:
        # No context available
        return _extract_keyword(en_solo) if len(en_solo.split()) > 2 else en_solo

    en_ctx = _translate_text(ctx_phrase)

    # If solo translation is short (≤2 words), trust it — Google just rephrased
    solo_words = en_solo.split()
    if len(solo_words) <= 2:
        return en_solo

    # Solo translation is long (3+ words) — check against context
    if en_solo.lower() in en_ctx.lower() or en_ctx.lower() in en_solo.lower():
        return _extract_keyword(en_solo)

    # Context disagrees with long solo — extract from context instead
    kw = _extract_keyword(en_ctx)
    if kw and len(kw.split()) <= 2:
        return kw
    return _extract_keyword(en_solo)


def _apply_word_replace(paragraphs):
    """Replace one word per clause with context-verified English translation.

    For each clause (split by ，。！？；…), picks a random Chinese word,
    translates it alone AND with surrounding context. If the solo translation
    appears in the context translation, it's used directly. Otherwise the
    context-informed meaning is used instead.

    Display format: English（中文词）— always 1-2 English words.
    """
    _ensure_jieba()
    import jieba

    # Collect all clauses with their word segmentations
    clauses = []
    for para in paragraphs:
        parts = re.split(r'(?<=[，。！？；…])', para)
        for part in parts:
            part = part.strip()
            if part and len(part) >= 6:
                words = list(jieba.cut(part))
                candidates = [(i, w) for i, w in enumerate(words)
                              if len(w) >= 2 and re.search(r'[一-鿿]', w)]
                if candidates:
                    clauses.append((para, words, candidates))

    if not clauses:
        return paragraphs[:]

    random.shuffle(clauses)
    selected = clauses[:MAX_TRANSLATIONS_PER_CHAPTER]

    # Translate each selected word with context verification
    replacements = []
    for para, words, candidates in selected:
        idx, word = random.choice(candidates)
        en = _translate_word_smart(word, words, idx)
        if en and en != word:
            replacements.append((para, word, en))

    if not replacements:
        return paragraphs[:]

    # Group by paragraph, sort by word length descending
    by_para = {}
    for para, word, en in replacements:
        for i, p in enumerate(paragraphs):
            if p is para:
                by_para.setdefault(i, []).append((word, en))
                break

    result = paragraphs[:]
    for i, reps in by_para.items():
        para = result[i]
        reps.sort(key=lambda x: -len(x[0]))
        for word, en in reps:
            if word in para:
                para = para.replace(word, f"{en}（{word}）", 1)
        result[i] = para

    return result


def disguise_chapter(title, paragraphs, replace_words=False):
    """Convert novel paragraphs to disguised code lines.

    Args:
        title: Chapter title
        paragraphs: List of paragraph strings
        replace_words: If True, replace one word per sentence with English(Chinese)
    """
    if replace_words:
        paragraphs = _apply_word_replace(paragraphs)

    all_novel_lines = []
    for para in paragraphs:
        lines = split_to_lines(para)
        all_novel_lines.extend(lines)

    if not all_novel_lines:
        return ["# (empty chapter)", "pass"], "python"

    gen = CodeGen()
    gen.gen_file_header(title)

    novel_idx = 0
    classes_to_gen = max(2, len(all_novel_lines) // 20)

    for c in range(classes_to_gen):
        cls_name = gen.gen_class()
        gen.gen_init(cls_name)

        # Generate 2-4 methods per class
        methods_count = random.randint(2, 4)
        for m in range(methods_count):
            if novel_idx >= len(all_novel_lines):
                break
            method_name = gen.gen_method()
            inserted = gen.gen_method_body(method_name, all_novel_lines, novel_idx)
            novel_idx += inserted
            gen.gen_method_close()

        gen.indent = 0
        gen._emit('')
        gen._emit('')

    # If we still have novel lines left, add more methods
    while novel_idx < len(all_novel_lines):
        method_name = gen.gen_method()
        inserted = gen.gen_method_body(method_name, all_novel_lines, novel_idx)
        novel_idx += inserted
        gen.gen_method_close()

    gen.gen_footer()

    return gen.lines, "python"


def disguise_text_replace(title, paragraphs):
    """Plain-text mode: replace one word per sentence with English(Chinese)."""
    modified = _apply_word_replace(paragraphs)
    full_text = ''.join(modified)
    lines = split_to_lines(full_text)
    return lines, "text"