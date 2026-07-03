/* MoYu Reader - Frontend */

const App = {
    bookId: null,
    chapters: [],
    currentChapterId: null,
    prevId: null,
    nextId: null,
    mode: 'replace',  // 'code' or 'replace'

    init() {
        // Mode toggle
        this.statusMode = document.getElementById('status-mode');
        this.statusMode.addEventListener('click', () => this.toggleMode());

        // Command palette
        this.paletteOverlay = document.getElementById('palette-overlay');
        this.paletteInput = document.getElementById('palette-input');
        this.editorContent = document.getElementById('code-lines');
        this.fileTree = document.getElementById('file-tree');
        this.navInfo = document.getElementById('nav-info');
        this.breadcrumbFile = document.getElementById('breadcrumb-file');
        this.statusLine = document.getElementById('status-line');
        this.statusChapter = document.getElementById('status-chapter');
        this.statusLang = document.getElementById('status-lang');

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'P') {
                e.preventDefault();
                this.togglePalette();
            }
            if (e.altKey && e.key === 'ArrowLeft') {
                e.preventDefault();
                this.goPrev();
            }
            if (e.altKey && e.key === 'ArrowRight') {
                e.preventDefault();
                this.goNext();
            }
            if (e.key === 'Escape') {
                this.closePalette();
            }
        });

        // Palette input
        this.paletteInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                this.loadBook(this.paletteInput.value.trim());
            }
        });

        // Nav buttons
        document.getElementById('btn-prev').onclick = () => this.goPrev();
        document.getElementById('btn-next').onclick = () => this.goNext();

        // Scroll tracking
        document.getElementById('editor-scroll').addEventListener('scroll', (e) => {
            const top = e.target.scrollTop;
            const lh = 20;
            const ln = Math.floor(top / lh) + 1;
            this.statusLine.textContent = `Ln ${ln}, Col 1`;
        });
    },

    togglePalette() {
        this.paletteOverlay.classList.toggle('visible');
        if (this.paletteOverlay.classList.contains('visible')) {
            this.paletteInput.focus();
            this.paletteInput.value = '';
        }
    },

    toggleMode() {
        this.mode = this.mode === 'code' ? 'replace' : 'code';
        if (this.mode === 'replace') {
            this.statusMode.textContent = '📝 EN';
            this.statusMode.title = 'Click to switch to pure Code mode';
        } else {
            this.statusMode.textContent = '📝 Code';
            this.statusMode.title = 'Click to switch to EN mix mode';
        }
        // Reload current chapter with new mode
        if (this.currentChapterId) {
            this.loadChapter(this.currentChapterId);
        }
    },

    closePalette() {
        this.paletteOverlay.classList.remove('visible');
    },

    async loadBook(url) {
        if (!url) return;
        this.paletteInput.disabled = true;
        try {
            const res = await fetch('/api/book/load', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url}),
            });
            const data = await res.json();
            if (!data.success) {
                this.showPaletteError(data.error);
                return;
            }
            this.bookId = data.book_id;
            this.chapters = data.chapters;
            this.closePalette();
            this.renderFileTree(data.title);
            this.statusChapter.textContent = `0/${data.chapters.length} chapters`;
            // Auto load first chapter
            if (data.chapters.length > 0) {
                this.loadChapter(data.chapters[0].id);
            }
        } catch (e) {
            this.showPaletteError('Network error');
        } finally {
            this.paletteInput.disabled = false;
        }
    },

    showPaletteError(msg) {
        const list = document.getElementById('palette-list');
        list.innerHTML = `<div class="palette-error">${msg}</div>`;
    },

    renderFileTree(title) {
        let html = `<div class="tree-folder"><span class="tree-folder-icon">▼</span><span class="tree-folder-name">src</span></div>`;
        html += `<div class="tree-folder"><span class="tree-folder-icon">▼</span><span class="tree-folder-name">core</span></div>`;
        html += `<div class="tree-files">`;
        for (const ch of this.chapters) {
            const fname = this._chapterFilename(ch);
            html += `<div class="tree-file" data-id="${ch.id}" data-name="${ch.name}" onclick="App.loadChapter('${ch.id}')">
                <span class="tree-file-icon">🐍</span><span class="tree-file-name">${fname}</span></div>`;
        }
        html += `</div>`;
        // Add some fake project files to make it look real
        html += `<div class="tree-folder"><span class="tree-folder-icon">▼</span><span class="tree-folder-name">tests</span></div>`;
        html += `<div class="tree-files" style="color:var(--text-dimmer)">`;
        html += `<div class="tree-file"><span class="tree-file-icon">🐍</span><span class="tree-file-name">test_main.py</span></div>`;
        html += `<div class="tree-file"><span class="tree-file-icon">🐍</span><span class="tree-file-name">test_utils.py</span></div>`;
        html += `</div>`;
        html += `<div class="tree-file"><span class="tree-file-icon">📄</span><span class="tree-file-name">requirements.txt</span></div>`;
        html += `<div class="tree-file"><span class="tree-file-icon">📄</span><span class="tree-file-name">config.yaml</span></div>`;
        this.fileTree.innerHTML = html;
    },

    _chapterFilename(ch) {
        // Real project-style filenames with chapter number from name (or fallback to index)
        const names = [
            'models', 'handlers', 'utils', 'services',
            'pipeline', 'parser', 'scheduler', 'processor',
            'transform', 'validator', 'cache', 'metrics',
            'serializer', 'middleware', 'adapter', 'client',
            'repository', 'builder', 'config_loader', 'logger',
            'auth', 'router', 'db', 'api',
            'types', 'constants', 'exceptions', 'helpers',
            'formatter', 'indexer', 'storage', 'queue',
        ];
        // Use extracted chapter number from name if available, else fall back to index
        const displayNum = ch.num || (ch.index + 1);
        const num = String(displayNum).padStart(2, '0');
        return `${names[ch.index % names.length]}_${num}.py`;
    },

    async loadChapter(chapterId) {
        if (!this.bookId) return;
        this.currentChapterId = chapterId;

        // Highlight in file tree
        const files = this.fileTree.querySelectorAll('.tree-file');
        files.forEach(f => f.classList.remove('active'));
        const active = this.fileTree.querySelector(`[data-id="${chapterId}"]`);
        if (active) active.classList.add('active');

        try {
            const res = await fetch(`/api/chapter/${this.bookId}/${chapterId}?mode=${this.mode}`);
            const data = await res.json();
            if (!data.success) return;

            this.prevId = data.prev_id;
            this.nextId = data.next_id;
            this.renderEditor(data);
            this.renderTab(data);
            this.updateNav(data);
            this.updateStatus(data);
        } catch (e) {}
    },

    renderEditor(data) {
        let html = '';
        const langMap = {python: 'Python', javascript: 'JavaScript', text: 'Plain Text'};
        this.statusLang.textContent = langMap[data.lang] || data.lang;

        for (let i = 0; i < data.lines.length; i++) {
            const line = data.lines[i];
            const ln = i + 1;
            const highlighted = data.lang === 'text'
                ? this.highlightTextLine(line)
                : this.highlightLine(line, data.lang);
            html += `<div class="code-line">
                <span class="line-number">${ln}</span>
                <span class="line-content">${highlighted}</span></div>`;
        }
        this.editorContent.innerHTML = html;

        // Scroll to top
        document.getElementById('editor-scroll').scrollTop = 0;
        this.statusLine.textContent = 'Ln 1, Col 1';
    },

    highlightLine(line, lang) {
        if (!line) return '';

        const commentChar = lang === 'javascript' ? '//' : '#';
        const trimmed = line.trimStart();
        const indent = line.substring(0, line.length - trimmed.length);

        if (trimmed.startsWith(commentChar)) {
            // Comment line = novel content, highlight as comment
            return `${this.escapeHtml(indent)}<span class="token-comment">${this.escapeHtml(trimmed)}</span>`;
        }

        // Code line: tokenize first, then colorize each token
        // This avoids the broken HTML problem from sequential regex replaces
        const tokens = this.tokenize(trimmed, lang);
        let result = this.escapeHtml(indent);
        for (const token of tokens) {
            if (token.type === 'plain') {
                result += this.escapeHtml(token.text);
            } else {
                result += `<span class="token-${token.type}">${this.escapeHtml(token.text)}</span>`;
            }
        }
        return result;
    },

    tokenize(text, lang) {
        // Break text into tokens: strings, keywords, identifiers, numbers, punctuation, whitespace, operators
        const tokens = [];
        let i = 0;

        const keywords = lang === 'javascript'
            ? ['function', 'const', 'let', 'var', 'return', 'if', 'else', 'for', 'while', 'class', 'new', 'null', 'true', 'false', 'async', 'await', 'import', 'from', 'try', 'catch', 'finally']
            : ['def', 'class', 'return', 'if', 'else', 'elif', 'for', 'while', 'import', 'from', 'try', 'except', 'finally', 'with', 'as', 'not', 'and', 'or', 'None', 'True', 'False', 'in', 'is', 'raise', 'break', 'continue', 'pass', 'yield', 'lambda', 'global'];

        const builtins = ['self', 'super', 'print', 'len', 'range', 'int', 'str', 'float', 'list', 'dict', 'tuple', 'set', 'bool', 'type', 'isinstance', 'hasattr', 'getattr', 'setattr'];

        const puncts = '(){}[]:,.;';

        while (i < text.length) {
            const ch = text[i];

            // Whitespace
            if (ch === ' ' || ch === '\t') {
                let j = i;
                while (j < text.length && (text[j] === ' ' || text[j] === '\t')) j++;
                tokens.push({text: text.substring(i, j), type: 'plain'});
                i = j;
                continue;
            }

            // String (single or double quote, including f-strings)
            if (ch === "'" || ch === '"') {
                let quote = ch;
                // Check for triple quotes
                let triple = text.substring(i, i+3);
                let endLen = 1;
                if (triple === quote.repeat(3)) {
                    endLen = 3;
                    let j = i + 3;
                    while (j < text.length - 2 && text.substring(j, j+3) !== quote.repeat(3)) j++;
                    if (j < text.length) j += 3;
                    tokens.push({text: text.substring(i, j), type: 'string'});
                    i = j;
                    continue;
                }
                let j = i + 1;
                while (j < text.length && text[j] !== quote) {
                    if (text[j] === '\\') j++;  // skip escaped
                    j++;
                }
                if (j < text.length) j++;  // include closing quote
                tokens.push({text: text.substring(i, j), type: 'string'});
                i = j;
                continue;
            }

            // Number
            if (/\d/.test(ch)) {
                let j = i;
                while (j < text.length && /[\d._]/.test(text[j])) j++;
                tokens.push({text: text.substring(i, j), type: 'number'});
                i = j;
                continue;
            }

            // Punctuation
            if (puncts.includes(ch)) {
                tokens.push({text: ch, type: 'punctuation'});
                i++;
                continue;
            }

            // Operators
            if ('=<>!+-*/%&|^~'.includes(ch)) {
                let j = i;
                while (j < text.length && '=<>!+-*/%&|^~'.includes(text[j])) j++;
                tokens.push({text: text.substring(i, j), type: 'operator'});
                i = j;
                continue;
            }

            // Decorator @
            if (ch === '@') {
                let j = i;
                while (j < text.length && /\w/.test(text[j])) j++;
                tokens.push({text: text.substring(i, j), type: 'keyword2'});
                i = j;
                continue;
            }

            // Word (identifier or keyword)
            if (/\w/.test(ch)) {
                let j = i;
                while (j < text.length && /\w/.test(text[j])) j++;
                const word = text.substring(i, j);

                // Check what follows: if word is 'def' or 'class', the next word is a function/class name
                if (word === 'def') {
                    tokens.push({text: word, type: 'keyword'});
                    // Look ahead for function name
                    let k = j;
                    while (k < text.length && text[k] === ' ') k++;
                    let nameEnd = k;
                    while (nameEnd < text.length && /\w/.test(text[nameEnd])) nameEnd++;
                    if (nameEnd > k) {
                        tokens.push({text: text.substring(j, k), type: 'plain'});  // spaces
                        tokens.push({text: text.substring(k, nameEnd), type: 'function'});
                        j = nameEnd;
                    }
                } else if (word === 'class') {
                    tokens.push({text: word, type: 'keyword'});
                    let k = j;
                    while (k < text.length && text[k] === ' ') k++;
                    let nameEnd = k;
                    while (nameEnd < text.length && /\w/.test(text[nameEnd])) nameEnd++;
                    if (nameEnd > k) {
                        tokens.push({text: text.substring(j, k), type: 'plain'});
                        tokens.push({text: text.substring(k, nameEnd), type: 'type'});
                        j = nameEnd;
                    }
                } else if (keywords.includes(word)) {
                    tokens.push({text: word, type: 'keyword'});
                } else if (builtins.includes(word)) {
                    tokens.push({text: word, type: 'keyword'});
                } else if (/^[A-Z]/.test(word)) {
                    tokens.push({text: word, type: 'type'});
                } else {
                    tokens.push({text: word, type: 'variable'});
                }
                i = j;
                continue;
            }

            // Anything else: plain
            tokens.push({text: ch, type: 'plain'});
            i++;
        }

        return tokens;
    },

    escapeHtml(s) {
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    highlightTextLine(line) {
        // Highlight English（中文）patterns in text mode
        if (!line) return '';
        // Pattern: ASCII word followed by （Chinese chars）
        const escaped = this.escapeHtml(line);
        const highlighted = escaped.replace(
            /([\wÀ-ɏ]+)（([一-鿿＀-￯　-〿·]+)）/g,
            '<span class="token-string">$1</span><span class="token-comment">（$2）</span>'
        );
        return highlighted;
    },

    renderTab(data) {
        // Build a chapter-like object for _chapterFilename
        const chObj = {index: data.index, num: data.chapter_num};
        const fname = this._chapterFilename(chObj);
        const tabsBar = document.getElementById('tabs-bar');
        // Remove old tabs except welcome
        tabsBar.querySelectorAll('.tab:not(#tab-welcome)').forEach(t => t.remove());
        // Add new tab
        const tab = document.createElement('div');
        tab.className = 'tab active';
        tab.innerHTML = `<span class="tab-icon">🐍</span><span class="tab-name">${fname}</span><span class="tab-close">✕</span>`;
        // Deactivate welcome tab
        document.getElementById('tab-welcome').classList.remove('active');
        tabsBar.appendChild(tab);

        this.breadcrumbFile.textContent = fname;
    },

    updateNav(data) {
        this.navInfo.textContent = data.title || `Chapter ${data.index + 1}`;
        document.getElementById('btn-prev').disabled = !data.prev_id;
        document.getElementById('btn-next').disabled = !data.next_id;
    },

    updateStatus(data) {
        this.statusChapter.textContent = `${data.index + 1}/${data.total} chapters`;
    },

    goPrev() {
        if (this.prevId) this.loadChapter(this.prevId);
    },

    goNext() {
        if (this.nextId) this.loadChapter(this.nextId);
    },
};

document.addEventListener('DOMContentLoaded', () => App.init());