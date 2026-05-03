import traceback
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    try:
        from app import app
        client = app.test_client()
        r = client.get('/feed')
        print('STATUS', r.status_code)
        data = r.data.decode('utf-8', errors='replace')
        print('BODY PREVIEW:\n', data[:1000])
    except Exception:
        traceback.print_exc()

if __name__ == '__main__':
    main()

