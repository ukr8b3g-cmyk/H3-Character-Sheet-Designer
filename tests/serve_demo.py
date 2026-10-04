"""Local UI acceptance harness, NOT a ComfyUI server or GPU integration test.

Run from the repository root: python tests/serve_demo.py
"""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from h3_character_sheet.preview import HTTP_MAX_BYTES, compile_preview_request


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != '/h3_character_sheet_designer/preview':
            self.send_error(404)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length > HTTP_MAX_BYTES or length < 1:
                self.send_error(413)
                return
            result = compile_preview_request(self.rfile.read(length), max_resolution=16384)
            status = 200
        except Exception as exc:
            result = {'error': {'code': 'validation', 'message': str(exc)}}
            status = 400
        data = json.dumps(result, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == '__main__':
    print('UI harness: http://127.0.0.1:8765/tests/browser/ (not ComfyUI)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
