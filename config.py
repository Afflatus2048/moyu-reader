import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Cache dir: use /tmp on Vercel, local dir otherwise
if os.environ.get('VERCEL'):
    CACHE_DIR = os.path.join('/tmp', 'moyu-reader', 'books')
else:
    CACHE_DIR = os.path.join(BASE_DIR, 'cache', 'books')

HOST = '127.0.0.1'
PORT = 5742
MAX_LINE_COLS = 76
REQUEST_DELAY = 0.5
REQUEST_TIMEOUT = 10